"""Stable public taxonomy identities. Private keys and salts never leave this module."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat

import yaml


class IdentityError(ValueError):
    """Safe diagnostic: never include private input values in the message."""


def load_private_config(value=None):
    """Read JSON/YAML from ZOTERO_TOPIC_CONFIG; never read credential files."""
    if value is None:
        value = os.environ.get('ZOTERO_TOPIC_CONFIG', '')
    try:
        config = yaml.safe_load(value) if isinstance(value, str) else value
    except yaml.YAMLError:
        raise IdentityError('Invalid private topic configuration syntax') from None
    fields = {'id_salt', 'publish_root_keys', 'legacy_aliases', 'retire_legacy_ids'}
    if not isinstance(config, dict) or set(config) - fields:
        raise IdentityError('Invalid private topic configuration fields')
    salt, roots = config.get('id_salt'), config.get('publish_root_keys')
    if not isinstance(salt, str) or len(salt.encode()) < 32:
        raise IdentityError('Topic identity salt must contain at least 32 bytes')
    if not isinstance(roots, list) or not roots or any(not isinstance(k, str) or not k.strip() for k in roots) or len(set(roots)) != len(roots):
        raise IdentityError('Select unique nonempty publication root keys')
    aliases, retired = config.get('legacy_aliases', {}), config.get('retire_legacy_ids', [])
    if not isinstance(aliases, dict) or any(not isinstance(k, str) or not k.startswith('zt-') or not isinstance(v, str) or not v for k, v in aliases.items()):
        raise IdentityError('Invalid reviewed legacy identity mapping')
    if not isinstance(retired, list) or any(not isinstance(k, str) or not k.startswith('zt-') for k in retired) or len(set(retired)) != len(retired):
        raise IdentityError('Invalid reviewed retired identities')
    if set(aliases) & set(retired):
        raise IdentityError('Conflicting reviewed legacy identities')
    return {'id_salt': salt, 'publish_root_keys': list(roots),
            'legacy_aliases': dict(aliases), 'retire_legacy_ids': list(retired)}


def public_id(collection_key, salt):
    return 'zotero:' + hmac.new(salt.encode(), collection_key.encode(), hashlib.sha256).hexdigest()[:32]


def _public_topic(topic):
    # The previous archive is also a boundary: only public schema fields survive.
    fields = ('id', 'name', 'path', 'catalog_path', 'parent_id', 'facet', 'active', 'retired', 'aliases')
    return {k: topic[k] for k in fields if k in topic}


def registry_from_collections(collections, previous_taxonomy, private_config):
    """Return (public taxonomy, private collection-key -> stable-ID mapping).

    Invalid snapshots raise IdentityError, leaving the caller's previous archive
    untouched. A reviewed legacy_aliases/retire_legacy_ids config resolves v1
    migration ambiguity; names are never approximately matched.
    """
    config = load_private_config(private_config)
    if not isinstance(collections, list) or not collections:
        raise IdentityError('Empty collection snapshot must not replace a valid taxonomy')
    previous_taxonomy = previous_taxonomy or {}
    previous = previous_taxonomy.get('topics', [])
    if not isinstance(previous, list) or any(not isinstance(t, dict) or not isinstance(t.get('id'), str) for t in previous):
        raise IdentityError('Invalid previous public taxonomy')
    previous_by_id = {t['id']: t for t in previous}
    if len(previous_by_id) != len(previous):
        raise IdentityError('Duplicate previous public topic identities')
    rows = {}
    for collection in collections:
        try:
            key, row = collection['key'], collection['data']
            name, parent = row['name'], row.get('parentCollection')
        except (KeyError, TypeError):
            raise IdentityError('Invalid collection snapshot') from None
        if parent is False or parent == '':
            parent = None  # Zotero root collections use parentCollection: false.
        if not isinstance(key, str) or not key or key in rows or not isinstance(name, str) or not name.strip() or not (parent is None or isinstance(parent, str)):
            raise IdentityError('Invalid or duplicate collection identity')
        rows[key] = {'name': name.strip(), 'parent': parent}
    # Validate the entire snapshot, including unpublished branches.
    paths, roots, skipped = {}, {}, {}
    def visit(key, stack=()):
        if key in paths:
            return
        if key in stack:
            raise IdentityError('Collection hierarchy contains a cycle')
        row = rows[key]
        parent = row['parent']
        if parent is not None:
            if parent not in rows:
                raise IdentityError('Collection hierarchy contains an orphan')
            visit(parent, (*stack, key))
        paths[key] = (paths[parent] + ' / ' if parent else '') + row['name']
        roots[key] = roots[parent] if parent else key
        skipped[key] = bool(re.match(r'^00(?:\s|$)', row['name'])) or (skipped[parent] if parent else False)
    for key in rows:
        visit(key)
    publish = set(config['publish_root_keys'])
    for key in publish:
        if key in rows and rows[key]['parent'] is not None:
            raise IdentityError('Publication scope must select root collections')
        if key not in rows and public_id(key, config['id_salt']) not in previous_by_id:
            raise IdentityError('Unknown publication root requires review')
    published_keys = [k for k in rows if roots[k] in publish and not skipped[k]]
    mapping = {key: public_id(key, config['id_salt']) for key in published_keys}
    if len(set(mapping.values())) != len(mapping):
        raise IdentityError('Public identity collision')
    # An opaque public key identifier detects accidental salt rotation without
    # tying identity to which roots the maintainer chooses to publish.
    identity_key_id = hmac.new(config['id_salt'].encode(), b'ai4s-public-topic-identity-v1', hashlib.sha256).hexdigest()[:32]
    if previous_taxonomy.get('identity_key_id') not in (None, identity_key_id):
        raise IdentityError('Publication identity change requires review')
    aliases = dict(previous_taxonomy.get('aliases', {}))
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in aliases.items()):
        raise IdentityError('Invalid previous topic aliases')
    if any(source.startswith('zotero:') or source == target for source, target in aliases.items()):
        raise IdentityError('Aliases cannot redirect permanent stable identities')
    paths_to_keys = {}
    for key in published_keys:
        paths_to_keys.setdefault(paths[key], []).append(key)
    reviewed = config['legacy_aliases']
    retired_legacy = set(config['retire_legacy_ids'])
    for old_id, old in previous_by_id.items():
        if not old_id.startswith('zt-') or old_id in aliases or old_id in retired_legacy:
            continue
        if old_id in reviewed:
            candidates = [reviewed[old_id]]
        else:
            candidates = paths_to_keys.get(old.get('path', ''), [])
        if len(candidates) != 1 or candidates[0] not in mapping:
            raise IdentityError('Legacy topic identity migration requires review')
        aliases[old_id] = mapping[candidates[0]]
    topics = []
    for key in published_keys:
        topic_id = mapping[key]
        prior = previous_by_id.get(topic_id)
        if prior is None:
            prior = next((previous_by_id[old] for old, target in aliases.items() if target == topic_id and old in previous_by_id), {})
        topics.append({'id': topic_id, 'name': rows[key]['name'], 'path': paths[key],
                       'catalog_path': prior.get('catalog_path', prior.get('path', paths[key])),
                       'parent_id': mapping.get(rows[key]['parent']), 'facet': mapping[roots[key]],
                       'active': True, 'retired': False,
                       'aliases': sorted(k for k, value in aliases.items() if value == topic_id)})
    active_ids = set(mapping.values())
    for topic_id, old in previous_by_id.items():
        if topic_id in active_ids or topic_id in aliases:
            continue
        retained = _public_topic(old)
        retained.update(active=False, retired=True)
        topics.append(retained)
    all_ids = {t['id'] for t in topics}
    if any(target not in all_ids for target in aliases.values()):
        raise IdentityError('Topic alias target is missing')
    if any(t.get('parent_id') and t['parent_id'] not in all_ids and t['parent_id'] not in aliases for t in topics):
        raise IdentityError('Public taxonomy contains an orphan')
    for topic in topics:
        if topic.get('parent_id') in aliases:
            topic['parent_id'] = aliases[topic['parent_id']]
    topics.sort(key=lambda t: (t.get('path', ''), t['id']))
    payload = {'topics': topics, 'aliases': dict(sorted(aliases.items())), 'identity_version': 'hmac-v1', 'identity_key_id': identity_key_id}
    fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {**payload, 'version': fingerprint, 'status': 'ok'}, mapping


def main():
    """Local migration preview; never print the private lookup or modify inputs."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collections', required=True, help='Local collection snapshot JSON')
    parser.add_argument('--previous', required=True, help='Previous public taxonomy/archive JSON')
    parser.add_argument('--private-config', required=True, help='0600 private identity YAML')
    parser.add_argument('--output', help='Local public candidate taxonomy JSON')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    path = Path(args.private_config)
    if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise IdentityError('Private topic configuration must be a regular 0600 file')
    if not args.dry_run and not args.output:
        parser.error('--output is required unless --dry-run is used')
    config = load_private_config(path.read_text())
    previous = json.loads(Path(args.previous).read_text())
    previous = previous.get('taxonomy', previous)
    candidate, _ = registry_from_collections(json.loads(Path(args.collections).read_text()), previous, config)
    before = {t['id']: t for t in previous.get('topics', [])}
    after = {t['id']: t for t in candidate['topics']}
    receipt = {'dry_run': args.dry_run, 'added_ids': sorted(set(after)-set(before)),
               'changed_ids': sorted(k for k in set(after)&set(before) if after[k] != before[k]),
               'retired_ids': sorted(k for k, t in after.items() if t.get('retired')),
               'aliases': candidate['aliases'], 'version': candidate['version']}
    if not args.dry_run:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + '.tmp')
        temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2))
        temporary.replace(output)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (IdentityError, OSError, json.JSONDecodeError) as error:
        import sys
        print(str(error) if isinstance(error, IdentityError) else 'Cannot read migration inputs', file=sys.stderr)
        sys.exit(1)
