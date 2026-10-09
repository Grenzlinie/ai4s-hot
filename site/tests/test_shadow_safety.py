"""Synthetic shadow/publication boundaries; no Zotero or model calls."""
import contextlib, copy, importlib.util, io, json, os, pathlib, sys, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'site'))
from topics_schema import validate_archive

def load_script():
    spec=importlib.util.spec_from_file_location('shadow_safety_script',ROOT/'scripts/run_topics_shadow.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def archive():
    return {'schema_version':1,'generated_at':'2026-10-09T00:00:00Z','taxonomy':{'topics':[{'id':'r','name':'Public root','parent_id':None}]},'items':[{'id':'public1','title':'Synthetic public title'}]}

class ShadowSafetyTests(unittest.TestCase):
    def invoke(self,module,folder,reader,core):
        src=folder/'input.json';src.write_text(json.dumps(archive()))
        out=folder/'public-shadow/index.json';receipt=folder/'public-shadow/receipt.json';stream=io.StringIO()
        with patch.dict(os.environ),patch.object(sys,'argv',['shadow','--input',str(src),'--output',str(out),'--receipt',str(receipt)]),patch.object(module,'read_taxonomy',side_effect=reader),patch.object(module,'classify_v2',side_effect=core),contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
            try: module.main()
            except SystemExit as error: stream.write(str(error))
        return out,receipt,stream.getvalue(),src
    def test_shadow_projects_public_output_without_private_corpus(self):
        m=load_script()
        def reader(*args):return ({**archive()['taxonomy'],'status':'ok'},[{'title':'PRIVATE_REFERENCE_SENTINEL','text':'PRIVATE_TEXT_SENTINEL'}])
        def core(items,taxonomy,corpus,**kwargs):
            self.assertTrue(kwargs['force']);self.assertIn('PRIVATE_TEXT_SENTINEL',str(corpus));return {'status':'ok','algorithm':'synthetic','classified':1,'unclassified':0}
        with tempfile.TemporaryDirectory() as tmp:
            out,receipt,logs,src=self.invoke(m,pathlib.Path(tmp),reader,core)
            self.assertEqual(json.loads(out.read_text())['schema_version'],2)
            self.assertFalse(json.loads(receipt.read_text())['quality_accepted'])
            self.assertEqual(json.loads(src.read_text())['schema_version'],1)
            self.assertNotIn('PRIVATE_',out.read_text()+receipt.read_text()+logs)
    def test_private_exception_is_sanitized_without_any_artifact(self):
        m=load_script()
        def reader(*args):raise RuntimeError('PRIVATE_API_VALUE_SENTINEL')
        with tempfile.TemporaryDirectory() as tmp:
            out,receipt,logs,_=self.invoke(m,pathlib.Path(tmp),reader,lambda *a,**k:None)
            self.assertFalse(out.exists());self.assertFalse(receipt.exists());self.assertNotIn('PRIVATE_API_VALUE_SENTINEL',logs)
    def test_invalid_classifier_public_projection_never_written(self):
        m=load_script()
        def core(items,*args,**kwargs):items[0]['private_reference']='PRIVATE_SENTINEL';return {'status':'ok'}
        with tempfile.TemporaryDirectory() as tmp:
            try: out,receipt,logs,_=self.invoke(m,pathlib.Path(tmp),lambda *a:({**archive()['taxonomy'],'status':'ok'},[]),core)
            except ValueError: self.assertFalse((pathlib.Path(tmp)/'public-shadow/index.json').exists())
            else:self.assertFalse(out.exists());self.assertFalse(receipt.exists())
    def test_nested_override_private_fields_rejected(self):
        payload=archive();payload['items'][0]['topic_override']={'private_key':'PRIVATE_SENTINEL'}
        with self.assertRaises(ValueError):validate_archive(payload)
    def test_nested_classification_private_fields_rejected(self):
        payload=archive();payload['taxonomy']['classification']={'private_corpus':'PRIVATE_SENTINEL'}
        with self.assertRaises(ValueError):validate_archive(payload)
    def test_duplicate_and_unknown_public_identity_rejected(self):
        p=archive();p['items']*=2
        with self.assertRaises(ValueError):validate_archive(p)
        p=archive();p['items'][0]['topic_ids']=['missing']
        with self.assertRaises(ValueError):validate_archive(p)

class ReclassifySafetyTests(unittest.TestCase):
    def test_selective_backfill_narrows_overrides_and_keeps_alias_migration(self):
        import argparse, topics_reclassify as module
        p=archive();p['schema_version']=2
        p['taxonomy']={'topics':[{'id':'old','name':'Public','parent_id':None}]}
        label={'id':'old','facet':'old','method':'local_lexical_v2','score':.5,'confidence':'low','status':'classified','public_reason':'Retained synthetic public receipt'}
        p['items']=[{'id':i,'title':'Public '+i,'topic_ids':['old'],'topic_leaf_ids':['old'],'topic_labels':[copy.deepcopy(label)]} for i in ('a','b')]
        validate_archive(p)
        taxonomy={'topics':[{'id':'r','name':'Public','parent_id':None}],'aliases':{'old':'r'},'status':'ok'}
        records=[{'item_id':i,'topic_ids':['old'],'reason':'Synthetic correction','created_at':'2026-10-09T00:00:00Z','author':'Test','version':1} for i in ('a','b')]
        overrides={'schema_version':1,'overrides':records}
        seen=[]
        def core(items,tax,refs,*args,**kwargs):
            seen.extend(i['id'] for i in items)
            self.assertEqual([r['item_id'] for r in kwargs['overrides_payload']['overrides']],['a'])
            self.assertEqual(items[0]['topic_ids'],['r'])
            self.assertEqual(items[0]['topic_labels'][0]['id'],'r')
            self.assertEqual(items[0]['topic_labels'][0]['facet'],'r')
            return {'status':'ok','classified':1,'unclassified':0}
        original=pathlib.Path.read_text
        original_exists=pathlib.Path.exists
        def reader(path,*args,**kwargs):
            return json.dumps(overrides) if path.name=='overrides.json' else original(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ),patch.object(module,'read_taxonomy',return_value=(taxonomy,[])),patch.object(module,'classify_v2',side_effect=core),patch.object(pathlib.Path,'read_text',reader),patch.object(pathlib.Path,'exists',lambda p: True if p.name=='overrides.json' else original_exists(p)),contextlib.redirect_stdout(io.StringIO()):
            src=pathlib.Path(tmp)/'input.json';src.write_text(json.dumps(p));out=pathlib.Path(tmp)/'output.json'
            module.run(argparse.Namespace(input=src,output=out,item=['a'],force=True))
            self.assertEqual(seen,['a']);saved=json.loads(out.read_text());self.assertEqual(saved['items'][1]['topic_leaf_ids'],['r'])
            self.assertEqual(saved['items'][1]['topic_labels'],[{**label,'id':'r','facet':'r'}])
    def test_initial_v1_partial_migration_rejected_before_private_read_or_output(self):
        import argparse,topics_reclassify as module
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ),patch.object(module,'read_taxonomy') as reader,patch.object(module,'classify_v2') as core:
            src=pathlib.Path(tmp)/'input.json';src.write_text(json.dumps(archive()));out=pathlib.Path(tmp)/'output.json'
            with self.assertRaises(ValueError):module.run(argparse.Namespace(input=src,output=out,item=['public1'],force=True))
            reader.assert_not_called();core.assert_not_called();self.assertFalse(out.exists())
    def test_v2_explicit_labels_require_receipts_but_v1_can_omit(self):
        p=archive();p['items'][0].update(topic_ids=['r'],topic_leaf_ids=['r'])
        validate_archive(p)
        p['schema_version']=2
        with self.assertRaises(ValueError):validate_archive(p)
        p['items'][0]['topic_labels']=[]
        with self.assertRaises(ValueError):validate_archive(p)
    def test_atomic_schema_rejection_preserves_previous_file(self):
        from topics_reclassify import atomic_write
        p=archive();p['items'][0]['private_reference']='PRIVATE_SENTINEL'
        with tempfile.TemporaryDirectory() as tmp:
            out=pathlib.Path(tmp)/'index.json';out.write_text('previous')
            with self.assertRaises(ValueError):atomic_write(out,p)
            self.assertEqual(out.read_text(),'previous');self.assertEqual(len(list(out.parent.iterdir())),1)

if __name__=='__main__':unittest.main()
