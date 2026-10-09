"""Independent synthetic regressions; these are not human quality gold."""
import copy,importlib.util,pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from topics_corpus import prepare,exact_match
from topics_decision import decide,DEFAULTS
from topics_schema import validate_archive
T=[{'id':'r','parent_id':None,'name':'Root','path':'Root'},{'id':'a','parent_id':'r','name':'Leaf','path':'Root / Leaf'}]
class CoreIndependentTests(unittest.TestCase):
    def test_standard_conflict_and_title_ambiguity(self):
        corpus=prepare([{'title':'Same title','text':'Private fixture A','doi':'10.1234/a','topics':['a']},{'title':'Same title','text':'Private fixture B','doi':'10.1234/b','topics':['a']}])
        self.assertEqual(exact_match({'title':'Same title'},corpus),[])
        self.assertEqual(exact_match({'title':'Same title','doi':'10.1234/c'},corpus),[])
    def test_multiaxis_not_global_top_three(self):
        topics=[];scores={}
        for i in range(4):
            topics.extend([{'id':f'r{i}','parent_id':None,'name':'Axis','path':f'Axis {i}'},{'id':f'l{i}','parent_id':f'r{i}','name':'Leaf','path':f'Axis {i} / Leaf'}])
            scores[f'r{i}']={'score':0,'definition_hit':False,'rules':[]};scores[f'l{i}']={'score':.8,'definition_hit':True,'cold_start':False,'rules':[],'public_terms':['scientific']}
        item={'title':'Synthetic scientific experiment','excerpt':'This scientific experiment supplies enough public evidence for each independent axis in the synthetic fixture.','type':'paper'}
        result=decide(item,topics,scores,1,[],DEFAULTS)
        self.assertEqual(set(result['topic_leaf_ids']),{f'l{i}' for i in range(4)})
    def test_definition_only_is_low_confidence(self):
        scores={'r':{'score':.1,'definition_hit':False,'cold_start':True,'public_terms':[],'rules':[]},'a':{'score':.9,'definition_hit':True,'cold_start':True,'public_terms':['material'],'rules':[]}}
        item={'title':'Material experiment','excerpt':'Synthetic scientific material experiment with sufficient public description to support a definition candidate.','type':'paper'}
        result=decide(item,T,scores,1,[],DEFAULTS)
        self.assertTrue(result['topic_labels']);self.assertTrue(all(x['confidence']=='low' for x in result['topic_labels']))
    def test_private_root_item_and_topic_fields_failclosed(self):
        archive={'schema_version':2,'taxonomy':{'topics':copy.deepcopy(T)},'items':[{'id':'1'}]}
        for level in ('root','item','topic'):
            payload=copy.deepcopy(archive);target=payload if level=='root' else payload['items'][0] if level=='item' else payload['taxonomy']['topics'][0];target['private_reference_text']='PRIVATE_SENTINEL'
            with self.subTest(level=level),self.assertRaises(ValueError):validate_archive(payload)
    def test_hierarchy_cycle_and_orphan_rejected(self):
        for topics in ([{'id':'a','parent_id':'missing'}],[{'id':'a','parent_id':'b'},{'id':'b','parent_id':'a'}]):
            with self.assertRaises(ValueError):validate_archive({'schema_version':2,'taxonomy':{'topics':topics},'items':[]})

class BenchmarkContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=pathlib.Path(__file__).resolve().parents[2]/'scripts/benchmark_topics.py';spec=importlib.util.spec_from_file_location('evaluation_benchmark',path);cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
    def test_rss_unit_normalization(self):
        class Usage:ru_maxrss=1024
        with patch.object(self.module.resource,'getrusage',return_value=Usage()),patch.object(self.module.sys,'platform','linux'):
            self.assertEqual(self.module.peak_rss_bytes(),1024*1024)
        with patch.object(self.module.resource,'getrusage',return_value=Usage()),patch.object(self.module.sys,'platform','darwin'):
            self.assertEqual(self.module.peak_rss_bytes(),1024)
    def test_insufficient_real_refs_never_padded(self):
        records=[{'id':str(i),'split':'dev','item':{'id':str(i),'url':f'https://example.org/{i}','title':f'Public fixture {i}'}} for i in range(200)]
        dataset={'taxonomy':{'topics':T},'records':records};refs=[{'title':'Private unrelated fixture','text':'PRIVATE_SENTINEL','topics':['a']}]
        with patch.dict(self.module.os.environ),patch('site_topics.read_taxonomy',return_value=({'topics':T,'status':'ok'},refs)),patch('topics_classifier.classify_v2') as classifier:
            receipt=self.module.stage(dataset,'lexical','cold')
        self.assertEqual(receipt['status'],'insufficient_references');self.assertEqual(receipt['reference_n'],1);classifier.assert_not_called();self.assertNotIn('PRIVATE',str(receipt));self.assertFalse(receipt['runtime_pass'])
if __name__=='__main__':unittest.main()

class EffectiveCacheTests(unittest.TestCase):
    def test_backend_change_invalidates_opaque_cache(self):
        import tempfile,json
        import topics_classifier
        with tempfile.TemporaryDirectory(prefix='ai4s-evaluation-core-') as directory:
            root=pathlib.Path(directory)
            (root/'catalog.yaml').write_text('version: test\nweb_facets:\n  content_kind: [web:paper]\n  domain: [web:materials]\ntopics:\n- path: Root\n  definition: Synthetic scientific definition\n  definition_status: authored\n  facet: Root\n  synonyms: [scientific]\n  include: [scientific]\n  exclude: []\n- path: Root / Leaf\n  definition: Synthetic material definition\n  definition_status: authored\n  facet: Root\n  synonyms: [material]\n  include: [material]\n  exclude: []\n')
            (root/'thresholds.yaml').write_text('backend: lexical\ncalibration_status: synthetic_test_only\n')
            (root/'overrides.json').write_text(json.dumps({'schema_version':1,'overrides':[]}))
            topics=[{'id':'r','path':'Root','parent_id':None,'name':'Root'},{'id':'a','path':'Root / Leaf','parent_id':'r','name':'Leaf'}]
            taxonomy={'topics':topics,'version':'fixture-v1'}
            items=[{'id':'1','title':'Scientific material experiment','excerpt':'An unrelated public scientific material experiment supplies enough evidence for this synthetic fixture only.','type':'paper'}]
            class FakeSemantic:
                def __init__(self,*args):pass
                def score(self,text):return {'r':.7,'a':.95}
            with patch.object(topics_classifier,'ROOT',root),patch.object(topics_classifier,'load_private_config',return_value={'id_salt':'synthetic-salt'}),patch('topics_semantic.SemanticCandidates',FakeSemantic):
                first=topics_classifier.classify_v2(items,taxonomy,[],backend='lexical');token=items[0]['topic_cache_token']
                second=topics_classifier.classify_v2(items,taxonomy,[],backend='semantic')
                self.assertEqual(second['classified'],1);self.assertNotEqual(token,items[0]['topic_cache_token']);self.assertEqual(items[0]['topic_backend'],'semantic')
                third=topics_classifier.classify_v2(items,taxonomy,[],backend='semantic');self.assertEqual(third['classified'],0)
