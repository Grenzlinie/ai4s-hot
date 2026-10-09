"""Validate public corrections and apply reviewed overrides after automatic labels.

CLI: python site/topics_curate.py --archive index.json --input corrections.json
     --output site/topics/overrides.json [--replace]
This writes a local reviewable file; it never commits, pushes or calls a service.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path


class CurationError(ValueError):
    pass


FIELDS = {'item_id', 'topic_ids', 'reason', 'created_at', 'author', 'version', 'history', 'status', 'definition_version'}
EVENT_FIELDS = FIELDS - {'item_id', 'history'}


def _topic_map(topics):
    if isinstance(topics, dict):
        topics = topics.get('topics', [])
    mapping = {t['id']: t for t in topics}
    if len(mapping) != len(topics):
        raise CurationError('Duplicate topic identity')
    return mapping


def _ids(items):
    return set(items) if isinstance(items, dict) else {p['id'] if isinstance(p, dict) else p for p in items}


def _validate_event(row, known, allow_retired, history=False):
    allowed = EVENT_FIELDS if history else FIELDS
    required = {'topic_ids', 'reason', 'created_at', 'author', 'version'}
    if not isinstance(row, dict) or set(row) - allowed or not required.issubset(row):
        raise CurationError('Invalid public override fields')
    labels = row['topic_ids']
    if not isinstance(labels, list) or len(labels) > 64 or any(not isinstance(t, str) or t not in known for t in labels) or len(set(labels)) != len(labels):
        raise CurationError('Unknown or duplicate override topic identity')
    if not allow_retired and any(known[t].get('retired') or known[t].get('active') is False for t in labels):
        raise CurationError('Retired override target requires review')
    for field, limit in (('reason', 1000), ('author', 120)):
        if not isinstance(row[field], str) or not row[field].strip() or len(row[field]) > limit:
            raise CurationError('Invalid public override provenance')
    version = row['version']
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise CurationError('Override version must be a positive integer')
    try:
        timestamp = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError
    except (AttributeError, ValueError, TypeError):
        raise CurationError('Override timestamp must be an ISO timestamp with timezone') from None
    if row.get('status', 'active') not in ('active', 'needs_review'):
        raise CurationError('Invalid override status')
    if 'definition_version' in row and (not isinstance(row['definition_version'], str) or not row['definition_version']):
        raise CurationError('Invalid override definition version')


def validate_overrides(payload, items, topics, *, allow_retired=False):
    """Return normalized records; reject the entire payload before any mutation."""
    if not isinstance(payload, dict) or set(payload) != {'schema_version', 'overrides'} or not isinstance(payload['schema_version'], int) or payload['schema_version'] != 1 or isinstance(payload['schema_version'], bool) or not isinstance(payload['overrides'], list):
        raise CurationError('Invalid public override document')
    known, item_ids = _topic_map(topics), _ids(items)
    seen, records = set(), []
    aliases = topics.get('aliases', {}) if isinstance(topics, dict) else {}
    for original in payload['overrides']:
        row = copy.deepcopy(original)
        if isinstance(row, dict) and isinstance(row.get('topic_ids'), list):
            row['topic_ids'] = [aliases.get(t, t) if isinstance(t, str) else t for t in row['topic_ids']]
            for event in row.get('history', []) if isinstance(row.get('history', []), list) else []:
                if isinstance(event, dict) and isinstance(event.get('topic_ids'), list):
                    event['topic_ids'] = [aliases.get(t, t) if isinstance(t, str) else t for t in event['topic_ids']]
        _validate_event(row, known, allow_retired)
        item_id = row.get('item_id')
        if not isinstance(item_id, str) or item_id not in item_ids or item_id in seen:
            raise CurationError('Unknown or conflicting override item identity')
        seen.add(item_id)
        history = row.get('history', [])
        if not isinstance(history, list) or len(history) > 1000:
            raise CurationError('Invalid override history')
        versions = set()
        for event in history:
            _validate_event(event, known, True, history=True)
            if event['version'] >= row['version'] or event['version'] in versions:
                raise CurationError('Conflicting override history versions')
            versions.add(event['version'])
        result = copy.deepcopy(row)
        result['topic_ids'] = sorted(result['topic_ids'])
        result.setdefault('history', [])
        result.setdefault('status', 'active')
        records.append(result)
    return sorted(records, key=lambda row: row['item_id'])


def _ancestors(ids, known):
    result = set()
    for topic_id in ids:
        seen = set()
        while topic_id:
            if topic_id in seen or topic_id not in known:
                raise CurationError('Invalid override topic hierarchy')
            seen.add(topic_id)
            result.add(topic_id)
            topic_id = known[topic_id].get('parent_id')
    return sorted(result)


def apply_overrides(items, taxonomy, overrides):
    """Apply manual labels last. Retired targets retain provenance for review.

    Receipts live under item.topic_override; the source file is never modified.
    Empty topic_ids is an explicit manual decision to clear automatic labels.
    """
    if isinstance(overrides, list):
        overrides = {'schema_version': 1, 'overrides': overrides}
    records = validate_overrides(overrides, items, taxonomy, allow_retired=True)
    known = _topic_map(taxonomy)
    by_id = {p['id']: p for p in items}
    plan = []
    for record in records:
        definition_changed = record.get('definition_version') is not None and taxonomy.get('definition_version') is not None and record['definition_version'] != taxonomy['definition_version']
        review = definition_changed or record['status'] == 'needs_review' or any(known[t].get('retired') or known[t].get('active') is False for t in record['topic_ids'])
        labels = record['topic_ids']
        # Store explicit most-specific labels; ancestors are a separate closure.
        explicit = [t for t in labels if not any(t in _ancestors([other], known) for other in labels if other != t)]
        closure = _ancestors(explicit, known)
        receipt = copy.deepcopy(record)
        receipt['status'] = 'needs_review' if review else 'active'
        plan.append((record['item_id'], explicit, closure, receipt, review))
    applied, needs_review = 0, 0
    for item_id, explicit, closure, receipt, review in plan:
        item = by_id[item_id]
        item['topic_override'] = receipt
        if review:
            needs_review += 1
            continue
        item.update(topic_leaf_ids=explicit, topic_ids=closure, topic_method='manual',
                    topic_labels=[{'id': t, 'facet': known[t].get('facet'), 'method': 'manual',
                                   'score': None, 'confidence': 'high', 'status': 'classified',
                                   'public_reason': receipt['reason']} for t in explicit],
                    topic_status='classified' if explicit else 'taxonomy_gap',
                    topic_version=hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest())
        if explicit:
            item['topic_scope'] = 'research'
        applied += 1
    return {'status': 'needs_review' if needs_review else 'ok', 'applied': applied, 'needs_review': needs_review}


def import_overrides(payload, existing, items, topics, *, replace=False):
    """Merge reviewed edits, rejecting conflicting replacements by default."""
    incoming = validate_overrides(payload, items, topics)
    previous = validate_overrides(existing, items, topics, allow_retired=True)
    merged = {row['item_id']: row for row in previous}
    for record in incoming:
        old = merged.get(record['item_id'])
        if old and record != old:
            if not replace or record['version'] <= old['version']:
                raise CurationError('Conflicting override requires an explicit newer replacement')
            event = {k: copy.deepcopy(v) for k, v in old.items() if k in EVENT_FIELDS}
            record['history'] = old['history'] + [event]
        merged[record['item_id']] = record
    return {'schema_version': 1, 'overrides': validate_overrides(
        {'schema_version': 1, 'overrides': list(merged.values())}, items, topics, allow_retired=True)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    archive = json.loads(Path(args.archive).read_text())
    incoming = json.loads(Path(args.input).read_text())
    output = Path(args.output)
    existing = json.loads(output.read_text()) if output.exists() else {'schema_version': 1, 'overrides': []}
    result = import_overrides(incoming, existing, archive['items'], archive['taxonomy'], replace=args.replace)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(output)
    print('Validated public overrides: ' + str(len(result['overrides'])))


if __name__ == '__main__':
    main()
