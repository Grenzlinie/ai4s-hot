"""Synthetic independent per-axis threshold and cache regressions."""
import copy,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'site'))
from topics_decision import decide,DEFAULTS
from topics_thresholds import validate_thresholds
import topics_classifier as classifier

def setup():
    topics=[];definitions=[];scores={}
    for root in ('A','B'):
        for suffix in ('','1','2'):
            ident=root+suffix;path=root+(' / '+suffix if suffix else '')
            topics.append({'id':ident,'path':path,'catalog_path':path,'parent_id':root if suffix else None,'name':ident})
            definitions.append({'path':path,'definition':'Scientific material definition','facet':root,'definition_status':'authored','synonyms':['material'],'include':['scientific'],'exclude':[]})
            scores[ident]={'score':.5 if suffix else .1,'definition_hit':bool(suffix),'cold_start':False,'public_terms':['scientific'],'rules':[]}
    return topics,{'version':'test','topics':definitions,'web_facets':{'content_kind':['web:paper'],'domain':['web:materials']}},scores
ITEM={'id':'public','title':'Scientific material experiment','excerpt':'Scientific material experiment has enough public evidence for independent synthetic classification.','type':'paper'}
class ThresholdAcceptance(unittest.TestCase):
    def test_semantic_and_fusion_evidence_survive_low_lexical_coverage(self):
        topics,_,scores=setup()
        for backend in ('semantic','fusion'):
            result=decide(ITEM,topics,scores,0,[],{**DEFAULTS,'backend':backend})
            self.assertEqual(result['topic_status'],'classified')
            self.assertTrue(result['topic_leaf_ids'])
            self.assertEqual(result['topic_method'],'local_'+backend+'_v2')
            self.assertTrue(all(r['method']=='local_'+backend+'_v2' for r in result['topic_labels']))
        lexical=decide(ITEM,topics,scores,0,[],{**DEFAULTS,'backend':'lexical'})
        self.assertEqual(lexical['topic_status'],'taxonomy_gap')
    def test_semantic_score_clamped_in_classifier_without_model_download(self):
        topics,catalog,_=setup();items=[copy.deepcopy(ITEM)];taxonomy={'version':'fixture','topics':topics}
        class FakeSemantic:
            def __init__(self,*args):pass
            def score(self,text):return {t['id']:1.2 if t['parent_id'] else -.2 for t in topics}
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'catalog.yaml').write_text(yaml.safe_dump(catalog));(root/'thresholds.yaml').write_text('backend: semantic\ncalibration_status: synthetic\n')
            with patch.object(classifier,'ROOT',root),patch.object(classifier,'load_private_config',return_value={'id_salt':'synthetic-private-salt'}),patch('topics_semantic.SemanticCandidates',FakeSemantic):
                classifier.classify_v2(items,taxonomy,[{'title':'Unrelated private reference','text':'unrelated example','topics':['A1']}])
            self.assertEqual(items[0]['topic_method'],'local_semantic_v2')
            self.assertTrue(items[0]['topic_labels']);self.assertTrue(all(0<=label['score']<=1 for label in items[0]['topic_labels']))
    def test_omitted_backend_gets_validated_lexical_default(self):
        _,catalog,_=setup()
        self.assertEqual(validate_thresholds({'calibration_status':'synthetic'},catalog)['backend'],'lexical')
    def test_axis_min_score_and_quota_do_not_consume_other_axis(self):
        topics,catalog,scores=setup()
        options=validate_thresholds({'calibration_status':'synthetic','facet_thresholds':{'A':{'min_score':.8,'max_per_facet':1},'B':{'min_score':.4,'max_per_facet':2}}},catalog)
        result=decide(ITEM,topics,scores,1,[],options);self.assertEqual(set(result['topic_leaf_ids']),{'B1','B2'})
        options['facet_thresholds']['A']['min_score']=.4
        self.assertEqual(set(decide(ITEM,topics,scores,1,[],options)['topic_leaf_ids']),{'A1','B1','B2'})
    def test_axis_relative_and_margin_independently_apply(self):
        topics,catalog,scores=setup()
        for ident in ('A2','B2'):scores[ident]['score']=.45
        config={**DEFAULTS,'facet_thresholds':{'A':{'relative_score':.95},'B':{'relative_score':.8}}}
        self.assertEqual(set(decide(ITEM,topics,scores,1,[],config)['topic_leaf_ids']),{'A1','B1','B2'})
        for ident in ('A1','A2','B1','B2'):scores[ident]['definition_hit']=False
        config={**DEFAULTS,'facet_thresholds':{'A':{'margin':.1},'B':{'margin':.01}}}
        self.assertEqual(set(decide(ITEM,topics,scores,1,[],config)['topic_leaf_ids']),{'A','B1','B2'})
    def test_invalid_numeric_private_fields_and_axes_failclosed(self):
        _,catalog,_=setup()
        for field in ('min_score','relative_score','margin','min_coverage'):
            for value in (float('nan'),float('inf'),-.1,1.1,True,'0.5'):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_thresholds({'calibration_status':'synthetic',field:value},catalog)
        for field,value in [('max_per_facet',3),('max_per_facet',True),('backend','remote'),('private_salt','PRIVATE_SENTINEL'),('facet_thresholds',{'Unknown':{}}),('facet_thresholds',{'A':{'private':'PRIVATE_SENTINEL'}}),('facet_thresholds',{'A':{'max_per_facet':0}}),('facet_thresholds',{'A':{'min_score':float('nan')}})]:
            with self.subTest(field=field,value=value),self.assertRaises(ValueError) as error:validate_thresholds({'calibration_status':'synthetic',field:value},catalog)
            self.assertNotIn('PRIVATE_SENTINEL',str(error.exception))
    def test_threshold_change_invalidates_cache_and_bad_options_stop_before_candidates(self):
        topics,catalog,_=setup();items=[copy.deepcopy(ITEM)];taxonomy={'version':'fixture','topics':topics}
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'catalog.yaml').write_text(yaml.safe_dump(catalog));path=root/'thresholds.yaml';options={'calibration_status':'synthetic','facet_thresholds':{'A':{'min_score':.4}}};path.write_text(yaml.safe_dump(options))
            with patch.object(classifier,'ROOT',root),patch.object(classifier,'load_private_config',return_value={'id_salt':'synthetic-private-salt'}):
                self.assertEqual(classifier.classify_v2(items,taxonomy,[])['classified'],1);old=items[0]['topic_cache_token']
                self.assertEqual(classifier.classify_v2(items,taxonomy,[])['classified'],0)
                options['facet_thresholds']['A']['min_score']=.6;path.write_text(yaml.safe_dump(options))
                self.assertEqual(classifier.classify_v2(items,taxonomy,[])['classified'],1);self.assertNotEqual(old,items[0]['topic_cache_token'])
                path.write_text('calibration_status: synthetic\nmin_score: .nan\n')
                with patch.object(classifier,'LexicalCandidates') as candidates,self.assertRaises(ValueError):classifier.classify_v2(items,taxonomy,[])
                candidates.assert_not_called()
if __name__=='__main__':unittest.main()
