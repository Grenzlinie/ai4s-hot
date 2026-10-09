"""Synthetic transactional failures and anonymous attempt sidecars."""
import argparse,copy,importlib.util,json,os,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'site'))
import collect,topics_classifier as classifier
from topics_schema import validate_archive
from update_status import validate_status,failure_receipt,write_status
from test_thresholds import setup,ITEM

class FailureRetentionTests(unittest.TestCase):
    def transaction(self,where):
        topics,catalog,_=setup();items=[{**ITEM,'id':'first'},{**ITEM,'id':'last'}];taxonomy={'topics':topics,'version':'fixture'};before=copy.deepcopy((items,taxonomy))
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'catalog.yaml').write_text(yaml.safe_dump(catalog));(root/'thresholds.yaml').write_text('calibration_status: synthetic\n')
            with patch.object(classifier,'ROOT',root),patch.object(classifier,'load_private_config',return_value={'id_salt':'synthetic'}):
                if where=='last':
                    original=classifier.LexicalCandidates.score;count=[0]
                    def scoring(obj,text):
                        count[0]+=1
                        if count[0]==2:raise RuntimeError('PRIVATE_SENTINEL')
                        return original(obj,text)
                    ctx=patch.object(classifier.LexicalCandidates,'score',scoring)
                else:ctx=patch.object(classifier,'apply_overrides',side_effect=RuntimeError('PRIVATE_SENTINEL'))
                with ctx,self.assertRaises(Exception) as caught:classifier.classify_v2(items,taxonomy,[],force=True)
        self.assertEqual((items,taxonomy),before)
        if where=='last':self.assertIsInstance(caught.exception,classifier.ClassificationUpdateError);self.assertNotIn('PRIVATE_SENTINEL',str(caught.exception));self.assertEqual(caught.exception.failed_item_id,'last')
    def test_last_item_error_does_not_commit_partial_classification(self):self.transaction('last')
    def test_curation_error_does_not_commit_any_item_or_taxonomy(self):self.transaction('curation')
    def test_sync_and_classification_failure_leave_archive_and_daily_and_skip_summary(self):
        for stage in ('taxonomy','classification'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TOPICS_MODE':'v2'}):
                root=pathlib.Path(tmp);data=root/'data';(data/'daily').mkdir(parents=True);index=data/'index.json';index.write_text(json.dumps({'items':[],'sources':[],'taxonomy':{'topics':[],'identity_version':'hmac-v1','status':'ok'}}));daily=data/'daily/old.json';daily.write_text('old daily');before=index.read_bytes()
                config=root/'config.json';config.write_text(json.dumps({'lookback_days':30,'max_items_per_source':1,'summary_budget':1,'sources':[{'id':'fixture','name':'Fixture','kind':'fixture'}]}))
                taxonomy={'topics':[],'identity_version':'hmac-v1','status':'stale' if stage=='taxonomy' else 'ok'}
                with patch.dict(collect.COLLECTORS,{'fixture':lambda *a:[]}),patch.object(collect.site_topics,'read_taxonomy',return_value=(taxonomy,[])),patch.object(collect.site_topics,'classify',side_effect=RuntimeError('PRIVATE_SENTINEL')),patch.object(collect,'summarize') as summary,self.assertRaises(collect.UpdateFailure) as caught:
                    collect.run(argparse.Namespace(config=config,data_dir=data,paper_export=None,source=None,no_summary=False,summary_budget=1))
                self.assertEqual(caught.exception.stage,stage);self.assertNotIn('PRIVATE_SENTINEL',str(caught.exception));summary.assert_not_called();self.assertEqual(index.read_bytes(),before);self.assertEqual(daily.read_text(),'old daily');self.assertEqual(list((data/'daily').iterdir()),[daily])
    def test_retired_receipt_preserved_and_unknown_or_active_history_rejected(self):
        label={'id':'retired','facet':'r','method':'manual','score':None,'confidence':'high','status':'classified','public_reason':'Public historical correction'}
        topics=[{'id':'r','parent_id':None,'name':'Root','path':'A'},{'id':'retired','parent_id':'r','name':'Old','path':'A / Old','active':False,'retired':True}]
        p={'schema_version':2,'items':[{'id':'public','topic_ids':[],'topic_leaf_ids':[],'topic_labels':[],'topic_history':[label]}],'taxonomy':{'topics':topics}}
        validate_archive(p)
        for ident in ('unknown','r'):
            invalid=copy.deepcopy(p);invalid['items'][0]['topic_history'][0]['id']=ident
            with self.assertRaises(ValueError):validate_archive(invalid)
        items=[{**ITEM,'topic_ids':['r','retired'],'topic_leaf_ids':['retired'],'topic_labels':[label]}];taxonomy={'topics':topics,'version':'fixture'};_,catalog,_=setup()
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'catalog.yaml').write_text(yaml.safe_dump(catalog));(root/'thresholds.yaml').write_text('calibration_status: synthetic\n')
            with patch.object(classifier,'ROOT',root),patch.object(classifier,'load_private_config',return_value={'id_salt':'synthetic'}):classifier.classify_v2(items,taxonomy,[])
        self.assertEqual(items[0]['topic_history'],[label]);validate_archive({'schema_version':2,'items':items,'taxonomy':taxonomy})
    def test_status_private_injection_rejected_and_unknown_item_not_published(self):
        receipt=failure_receipt('classification','2026-10-09T00:00:00Z','PRIVATE_UNKNOWN')
        with self.assertRaises(ValueError):validate_status({**receipt,'private_reference':'PRIVATE_SENTINEL'})
        for field,value in [('stage','private'),('error_type','PRIVATE_SENTINEL'),('failed_item_id',{}),('run_url','https://example.org/private')]:
            with self.subTest(field=field),self.assertRaises(ValueError):validate_status({**receipt,field:value})
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'data').mkdir();(root/'data/index.json').write_text(json.dumps({'schema_version':2,'generated_at':'2026-10-08T00:00:00Z','items':[],'taxonomy':{'topics':[]}}));report=root/'report.json';report.write_text(json.dumps(receipt))
            published=write_status(root,'error','classification',report)
            self.assertNotIn('failed_item_id',published);self.assertNotIn('PRIVATE', (root/'update-status.json').read_text());self.assertEqual(published['last_success'],'2026-10-08T00:00:00Z')
    def test_status_invalid_timestamp_error_does_not_repeat_input(self):
        receipt=failure_receipt('classification','2026-10-09T00:00:00Z');receipt['last_attempt']='PRIVATE_SENTINEL'
        with self.assertRaises(ValueError) as error:validate_status(receipt)
        self.assertNotIn('PRIVATE_SENTINEL',str(error.exception))
    def test_maintenance_probe_exercises_both_failures_without_api_or_summary(self):
        spec=importlib.util.spec_from_file_location('failure_probe_under_test',ROOT/'scripts/probe_update_failure.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
        topics,_,_=setup();p={'schema_version':2,'items':[{**ITEM,'first_seen':collect.NOW.isoformat()}],'sources':[],'taxonomy':{'topics':topics,'version':'fixture','identity_version':'hmac-v1','status':'ok'}}
        env={'TOPICS_MODE':'v2','ZOTERO_TOPIC_CONFIG':json.dumps({'id_salt':'private-synthetic-salt-0123456789abcdef','publish_root_keys':['synthetic']})}
        for stage in ('taxonomy','classification'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,env,clear=True):
                root=pathlib.Path(tmp);index=root/'index.json';index.write_text(json.dumps(p));before=index.read_bytes();report=root/'failure.json'
                self.assertEqual(probe.run(stage,root,report),2);self.assertEqual(index.read_bytes(),before);receipt=json.loads(report.read_text());self.assertEqual(receipt['stage'],stage);self.assertNotIn('PRIVATE',str(receipt))
    def test_retention_workflow_gates_commit_and_restores_immutable_data(self):
        text=(ROOT/'.github/workflows/ai4s-pages.yml').read_text()
        self.assertIn("if: steps.collect.outcome == 'success' && steps.candidate.outcome == 'success'",text)
        self.assertIn('archive "$ARCHIVE_SHA" data | tar',text);self.assertIn('--data-dir "$RUNNER_TEMP/retained/data"',text);self.assertIn('--mode retention',text);self.assertIn('--failure-report "$RUNNER_TEMP/update-failure.json"',text)
if __name__=='__main__':unittest.main()
