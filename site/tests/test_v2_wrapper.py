"""Actual opt-in wrapper failure/scope contracts with synthetic Zotero only."""
import copy, json, os, pathlib, sys, unittest
from unittest.mock import MagicMock, patch
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'site'))
import site_topics as wrapper
from topics_identity import registry_from_collections
CONFIG={'id_salt':'synthetic-private-salt-0123456789abcdef','publish_root_keys':['PRIVATE_ROOT']}
ROWS=[{'key':'PRIVATE_ROOT','data':{'name':'Root','parentCollection':False}}, {'key':'PRIVATE_CHILD','data':{'name':'Child','parentCollection':'PRIVATE_ROOT'}}, {'key':'PRIVATE_OUTSIDE','data':{'name':'Unpublished','parentCollection':False}}]
ENV={'TOPICS_MODE':'v2','ZOTERO_ID':'SYNTHETIC_ID','ZOTERO_KEY':'PRIVATE_API_SENTINEL','ZOTERO_TOPIC_CONFIG':json.dumps(CONFIG)}
class WrapperAcceptance(unittest.TestCase):
    def setUp(self):
        self.previous,self.keys=registry_from_collections(ROWS,{},CONFIG)
        self.previous['last_success']='2026-10-08T00:00:00Z'
    def call(self,client,env=ENV):
        with patch.dict(os.environ,env,clear=True),patch.object(wrapper.zotero,'Zotero',return_value=client):
            return wrapper.read_taxonomy(self.previous,'2026-10-09T00:00:00Z')
    def assert_preserved(self,public,corpus,status):
        self.assertEqual(public['status'],status);self.assertEqual(public['topics'],self.previous['topics']);self.assertEqual(public['last_success'],self.previous['last_success']);self.assertEqual(corpus,[]);self.assertNotIn('PRIVATE_API_SENTINEL',json.dumps(public))
    def test_failed_read_retains_last_valid_without_exception_message(self):
        client=MagicMock();client.collections.side_effect=RuntimeError('PRIVATE_API_SENTINEL')
        before=copy.deepcopy(self.previous);public,corpus=self.call(client)
        self.assert_preserved(public,corpus,'stale');self.assertEqual(public['error_type'],'RuntimeError');self.assertEqual(self.previous,before)
    def test_empty_snapshot_retains_last_valid_and_stops_item_read(self):
        client=MagicMock();client.everything.return_value=[]
        public,corpus=self.call(client);self.assert_preserved(public,corpus,'stale');client.top.assert_not_called()
    def test_unconfigured_retains_last_valid_without_client(self):
        with patch.dict(os.environ,{'TOPICS_MODE':'v2'},clear=True),patch.object(wrapper.zotero,'Zotero') as client:
            public,corpus=wrapper.read_taxonomy(self.previous,'later')
        self.assert_preserved(public,corpus,'unconfigured');client.assert_not_called()
    def test_stale_wrapper_does_not_reclassify_or_erase_last_labels(self):
        items=[{'id':'public','topic_ids':[self.keys['PRIVATE_CHILD']],'topic_leaf_ids':[self.keys['PRIVATE_CHILD']]}]
        before=copy.deepcopy(items)
        with patch.dict(os.environ,{'TOPICS_MODE':'v2'},clear=True),patch('topics_classifier.classify_v2') as core:
            receipt=wrapper.classify(items,{**self.previous,'status':'stale'},[])
        self.assertEqual(receipt,{'status':'unavailable','classified':0});self.assertEqual(items,before);core.assert_not_called()
    def test_only_scoped_research_rows_enter_private_in_memory_corpus(self):
        def item(title,collections,kind='journalArticle'):
            return {'data':{'title':title,'abstractNote':'PRIVATE_TEXT_SENTINEL','collections':collections,'itemType':kind,'private':'PRIVATE_FIELD_SENTINEL','key':'PRIVATE_ITEM_KEY'}}
        client=MagicMock();client.everything.side_effect=[ROWS,[item('Scoped',['PRIVATE_CHILD']),item('Outside',['PRIVATE_OUTSIDE']),item('Note',['PRIVATE_CHILD'],'note'),item('Mixed',['PRIVATE_CHILD','PRIVATE_OUTSIDE']),item('Attachment',['PRIVATE_CHILD'],'attachment')]]
        public,corpus=self.call(client)
        self.assertEqual([r['title'] for r in corpus],['Scoped','Mixed']);self.assertTrue(all(r['topics']==[self.keys['PRIVATE_CHILD']] for r in corpus))
        self.assertTrue(all(set(r)=={'title','text','topics','doi','url','extra'} for r in corpus));self.assertNotIn('PRIVATE_FIELD_SENTINEL',str(corpus));self.assertNotIn('PRIVATE',json.dumps(public));self.assertNotIn('Scoped',json.dumps(public));self.assertEqual(public['status'],'ok')

class PublicCatalogCoverage(unittest.TestCase):
    def test_actual_baseline_topics_bind_one_to_one_to_authored_definitions(self):
        # Deliberately inspect only taxonomy, never evaluation records/holdout titles.
        topics=json.loads((ROOT/'site/topics/evaluation/baseline-input.json').read_text())['taxonomy']['topics']
        catalog=yaml.safe_load((ROOT/'site/topics/catalog.yaml').read_text())['topics']
        paths=[t.get('catalog_path',t['path']) for t in topics];definitions=[d['path'] for d in catalog]
        self.assertEqual(len(paths),53);self.assertEqual(len(set(paths)),len(paths));self.assertEqual(len(set(definitions)),len(definitions));self.assertEqual(set(paths),set(definitions))
        for definition in catalog:
            self.assertTrue(definition['definition'].strip());self.assertEqual(definition['definition_status'],'authored')
            for field in ('synonyms','include','exclude'):self.assertIsInstance(definition[field],list)

if __name__=='__main__':unittest.main()
