"""Synthetic identity/config/curation contracts; no credential or service access."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import re
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
identity=module('identity_under_test','site/topics_identity.py')
curate=module('curate_under_test','site/topics_curate.py')
configure=module('configure_identity_under_test','scripts/configure.py')


def collection(key,name,parent=None):
    return {'key':key,'data':{'name':name,'parentCollection':parent},'private':'PRIVATE_RECORD'}

CONFIG={'id_salt':'SYNTHETIC_PRIVATE_SALT_0123456789abcdef','publish_root_keys':['PRIVATE_ROOT']}
ROWS=[collection('PRIVATE_ROOT','Research'),collection('PRIVATE_CHILD','Materials','PRIVATE_ROOT'),collection('PRIVATE_SKIP','00 Inbox','PRIVATE_ROOT'),collection('PRIVATE_HIDDEN','Hidden','PRIVATE_SKIP'),collection('PRIVATE_UNPUBLISHED','Personal')]


class IdentityAcceptance(unittest.TestCase):
    def test_stable_hmac_rename_move_and_public_boundary(self):
        public,mapping=identity.registry_from_collections(ROWS,{},CONFIG)
        self.assertEqual(set(mapping),{'PRIVATE_ROOT','PRIVATE_CHILD'})
        self.assertNotIn('PRIVATE',json.dumps(public))
        self.assertTrue(all(re.fullmatch(r'zotero:[0-9a-f]{32}',v) for v in mapping.values()))
        changed=copy.deepcopy(ROWS)
        changed[0]['data']['name']='Renamed research'
        changed.append(collection('PRIVATE_SECOND','Methods','PRIVATE_ROOT'))
        changed[1]['data'].update(name='Renamed material',parentCollection='PRIVATE_SECOND')
        after,next_mapping=identity.registry_from_collections(changed,public,CONFIG)
        self.assertEqual(mapping['PRIVATE_CHILD'],next_mapping['PRIVATE_CHILD'])
        self.assertEqual(mapping['PRIVATE_ROOT'],next_mapping['PRIVATE_ROOT'])
        self.assertEqual(next(t for t in after['topics'] if t['id']==mapping['PRIVATE_CHILD'])['parent_id'],next_mapping['PRIVATE_SECOND'])
        self.assertEqual(next(t for t in after['topics'] if t['id']==mapping['PRIVATE_CHILD'])['catalog_path'],'Research / Materials')

    def test_zotero_false_root_parent_is_accepted(self):
        rows=copy.deepcopy(ROWS)
        rows[0]['data']['parentCollection']=False
        public,mapping=identity.registry_from_collections(rows,{},CONFIG)
        self.assertIsNone(next(t for t in public['topics'] if t['id']==mapping['PRIVATE_ROOT'])['parent_id'])

    def test_v1_alias_migration_and_retired_nodes(self):
        old={'topics':[{'id':'zt-oldroot','name':'Research','path':'Research','parent_id':None},{'id':'zt-oldchild','name':'Materials','path':'Research / Materials','parent_id':'zt-oldroot'}]}
        public,mapping=identity.registry_from_collections(ROWS,old,CONFIG)
        self.assertEqual(public['aliases']['zt-oldchild'],mapping['PRIVATE_CHILD'])
        reduced=[row for row in ROWS if row['key']!='PRIVATE_CHILD']
        after,_=identity.registry_from_collections(reduced,public,CONFIG)
        retired=next(t for t in after['topics'] if t['id']==mapping['PRIVATE_CHILD'])
        self.assertTrue(retired['retired'])
        self.assertFalse(retired['active'])
        self.assertEqual(after['aliases'],public['aliases'])

    def test_invalid_snapshot_fails_without_mutating_previous(self):
        previous,_=identity.registry_from_collections(ROWS,{},CONFIG)
        before=copy.deepcopy(previous)
        invalid=[[],[collection('A','A','missing')],[collection('A','A','B'),collection('B','B','A')],ROWS+[ROWS[0]]]
        for rows in invalid:
            with self.subTest(rows=len(rows)),self.assertRaises(identity.IdentityError):
                identity.registry_from_collections(rows,previous,CONFIG)
            self.assertEqual(previous,before)

    def test_ambiguous_legacy_paths_require_explicit_review(self):
        rows=ROWS+[collection('PRIVATE_OTHER','Materials','PRIVATE_ROOT')]
        old={'topics':[{'id':'zt-legacy','path':'Research / Materials','name':'Materials','parent_id':None}]}
        with self.assertRaises(identity.IdentityError):
            identity.registry_from_collections(rows,old,CONFIG)
        public,mapping=identity.registry_from_collections(rows,old,{**CONFIG,'legacy_aliases':{'zt-legacy':'PRIVATE_CHILD'}})
        self.assertEqual(public['aliases']['zt-legacy'],mapping['PRIVATE_CHILD'])
        self.assertNotEqual(mapping['PRIVATE_CHILD'],mapping['PRIVATE_OTHER'])

    def test_salt_rotation_is_rejected_but_publication_scope_can_change(self):
        public,_=identity.registry_from_collections(ROWS,{},CONFIG)
        with self.assertRaises(identity.IdentityError):
            identity.registry_from_collections(ROWS,public,{**CONFIG,'id_salt':'changed_salt_012345678901234567890123456'})
        changed,_=identity.registry_from_collections(ROWS,public,{**CONFIG,'publish_root_keys':['PRIVATE_UNPUBLISHED']})
        self.assertEqual(sum(t['active'] for t in changed['topics']),1)
        self.assertTrue(any(t['retired'] for t in changed['topics']))

    def test_environment_config_errors_do_not_echo_private_values(self):
        for value in ('id_salt: [PRIVATE_BROKEN',json.dumps({**CONFIG,'unexpected':'PRIVATE_VALUE'}),json.dumps({**CONFIG,'id_salt':'PRIVATE_SHORT'})):
            with self.subTest(value=value[:10]):
                with self.assertRaises(identity.IdentityError) as error:
                    identity.load_private_config(value)
                self.assertNotIn('PRIVATE',str(error.exception))

    def test_migration_dry_run_has_no_file_writes_or_private_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'collections.json').write_text(json.dumps(ROWS))
            (root/'previous.json').write_text('{}')
            private=root/'private.yaml';private.write_text(json.dumps(CONFIG));private.chmod(0o600)
            output=root/'candidate.json'
            stdout=io.StringIO()
            with patch.object(sys,'argv',['topics_identity.py','--collections',str(root/'collections.json'),'--previous',str(root/'previous.json'),'--private-config',str(private),'--output',str(output),'--dry-run']),contextlib.redirect_stdout(stdout):
                identity.main()
            self.assertFalse(output.exists())
            self.assertNotIn('PRIVATE',stdout.getvalue())
            self.assertTrue(json.loads(stdout.getvalue())['dry_run'])


class PrivateSyncAcceptance(unittest.TestCase):
    def test_init_is_0600_and_never_replaces_existing_salt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'topics.yaml'
            configure.initialize_private_topics(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            original=path.read_bytes()
            with self.assertRaises(FileExistsError):configure.initialize_private_topics(path)
            self.assertEqual(path.read_bytes(),original)

    def test_private_secret_stdin_only_and_validation_precedes_all_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'private.yaml'
            path.write_text(json.dumps(CONFIG));path.chmod(0o600)
            argv=['configure.py','--topics-private',str(path)]
            output=io.StringIO()
            with patch.object(sys,'argv',argv),patch.object(configure,'read_credentials',return_value={'OPENAI_API_KEY':'SYNTHETIC_API'}),patch.object(configure,'read_config',return_value=('llm: {}','mock')),patch.object(configure.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run,contextlib.redirect_stdout(output):
                configure.main()
            private_call=next(c for c in run.call_args_list if 'ZOTERO_TOPIC_CONFIG' in c.args[0])
            self.assertIn(CONFIG['id_salt'],private_call.kwargs['input'])
            self.assertNotIn('PRIVATE',str([c.args[0] for c in run.call_args_list]))
            self.assertNotIn('PRIVATE',output.getvalue())
            public_call=next(c for c in run.call_args_list if 'CUSTOM_CONFIG' in c.args[0])
            self.assertNotIn('PRIVATE',public_call.kwargs['input'])
            path.chmod(0o644)
            with patch.object(sys,'argv',argv),patch.object(configure,'read_credentials',return_value={}),patch.object(configure,'read_config',return_value=('llm: {}','mock')),patch.object(configure.subprocess,'run') as run:
                with self.assertRaises(ValueError):configure.main()
                run.assert_not_called()

    def test_private_identity_fields_rejected_in_public_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'public.yaml'
            path.write_text('llm:\n  generation_kwargs:\n    model: mock\nid_salt: PRIVATE_VALUE\n')
            with self.assertRaises(ValueError):configure.read_config(path)


class CurationAcceptance(unittest.TestCase):
    def setUp(self):
        self.taxonomy,self.mapping=identity.registry_from_collections(ROWS,{},CONFIG)
        self.root=self.mapping['PRIVATE_ROOT'];self.child=self.mapping['PRIVATE_CHILD']
        self.items=[{'id':'public-item','topic_ids':[],'topic_leaf_ids':[],'topic_method':'automatic'}]
        self.record={'item_id':'public-item','topic_ids':[self.child],'reason':'Public correction','created_at':'2026-10-09T00:00:00Z','author':'local visitor','version':1}
        self.payload={'schema_version':1,'overrides':[self.record]}

    def test_manual_override_wins_including_clear_and_v2_receipt(self):
        result=curate.apply_overrides(self.items,self.taxonomy,self.payload)
        self.assertEqual(result['applied'],1)
        self.assertEqual(set(self.items[0]['topic_ids']),{self.root,self.child})
        self.assertEqual(self.items[0]['topic_method'],'manual')
        self.assertEqual(self.items[0]['topic_labels'][0]['public_reason'],'Public correction')
        cleared=copy.deepcopy(self.payload);cleared['overrides'][0]['topic_ids']=[]
        curate.apply_overrides(self.items,self.taxonomy,cleared)
        self.assertEqual(self.items[0]['topic_ids'],[])
        self.assertEqual(self.items[0]['topic_method'],'manual')

    def test_unknown_conflicting_private_or_malformed_edits_fail_atomically(self):
        bad_records=[{**self.record,'topic_ids':['unknown']},{**self.record,'item_id':'unknown'},{**self.record,'collection_key':'PRIVATE'},{**self.record,'version':True},{**self.record,'created_at':'bad'},{**self.record,'topic_ids':[self.child,self.child]}]
        before=copy.deepcopy(self.items)
        for row in bad_records:
            with self.subTest(row=list(row)),self.assertRaises(curate.CurationError):
                curate.apply_overrides(self.items,self.taxonomy,{'schema_version':1,'overrides':[row]})
            self.assertEqual(self.items,before)
        with self.assertRaises(curate.CurationError):
            curate.validate_overrides({'schema_version':1,'overrides':[self.record,self.record]},self.items,self.taxonomy)

    def test_retired_targets_need_review_and_keep_history_and_automatic_labels(self):
        taxonomy=copy.deepcopy(self.taxonomy)
        next(t for t in taxonomy['topics'] if t['id']==self.child).update(retired=True,active=False)
        self.items[0].update(topic_ids=[self.root],topic_leaf_ids=[self.root])
        with self.assertRaises(curate.CurationError):curate.validate_overrides(self.payload,self.items,taxonomy)
        result=curate.apply_overrides(self.items,taxonomy,self.payload)
        self.assertEqual(result['needs_review'],1)
        self.assertEqual(self.items[0]['topic_ids'],[self.root])
        self.assertEqual(self.items[0]['topic_override']['status'],'needs_review')
        self.assertEqual(self.items[0]['topic_override']['reason'],self.record['reason'])

    def test_import_conflict_requires_new_version_and_preserves_history(self):
        newer={'schema_version':1,'overrides':[{**self.record,'topic_ids':[self.root],'version':2}]}
        with self.assertRaises(curate.CurationError):curate.import_overrides(newer,self.payload,self.items,self.taxonomy)
        merged=curate.import_overrides(newer,self.payload,self.items,self.taxonomy,replace=True)
        self.assertEqual(merged['overrides'][0]['history'][0]['topic_ids'],[self.child])
        self.assertEqual(merged['overrides'][0]['version'],2)

    def test_legacy_alias_is_resolved_before_validating_override(self):
        self.taxonomy['aliases']={'zt-old':self.child}
        payload={'schema_version':1,'overrides':[{**self.record,'topic_ids':['zt-old']}]}
        normalized=curate.validate_overrides(payload,self.items,self.taxonomy)
        self.assertEqual(normalized[0]['topic_ids'],[self.child])

    def test_definition_conflict_requires_review_without_overwriting_labels(self):
        self.taxonomy['definition_version']='v2'
        self.record['definition_version']='v1'
        before=copy.deepcopy(self.items[0]['topic_ids'])
        result=curate.apply_overrides(self.items,self.taxonomy,self.payload)
        self.assertEqual(result['needs_review'],1)
        self.assertEqual(self.items[0]['topic_ids'],before)
        self.assertEqual(self.items[0]['topic_override']['definition_version'],'v1')


if __name__=='__main__':unittest.main()
