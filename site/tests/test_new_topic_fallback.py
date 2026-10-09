"""Independent new-directory regressions with synthetic public names only."""
import copy,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from topics_catalog import definition_for_topic,validate_catalog
from topics_candidates import LexicalCandidates
from topics_decision import decide,DEFAULTS

TOPICS=[{'id':'root','name':'Scientific methods','path':'Scientific methods','parent_id':None},
        {'id':'new','name':'Quantum widgets','path':'Scientific methods / Quantum widgets','parent_id':'root'}]
CATALOG={'version':'synthetic-v1','topics':[{'path':'Scientific methods','definition':'General public scientific methods.','synonyms':['scientific'],'include':['scientific'],'exclude':[],'definition_status':'authored','facet':'Scientific methods','rules':[]}],
         'web_facets':{'content_kind':['web:paper'],'domain':['web:general_ai']}}
class NewTopicFallback(unittest.TestCase):
    def test_new_empty_topic_has_name_context_candidate_and_low_receipt(self):
        catalog=copy.deepcopy(CATALOG);topics=copy.deepcopy(TOPICS)
        candidate=LexicalCandidates([],topics,catalog)
        item={'title':'Quantum widgets for research','excerpt':'This scientific experiment studies Quantum widgets through a controlled public measurement protocol and reports reproducible observations.','type':'paper'}
        scores,coverage=candidate.score(item['title']+' '+item['excerpt'])
        self.assertTrue(scores['new']['definition_hit']);self.assertGreater(scores['new']['score'],0);self.assertTrue(scores['new']['cold_start']);self.assertEqual(scores['new']['public_terms'],['Quantum widgets'])
        result=decide(item,topics,scores,coverage,[],{**DEFAULTS,'min_coverage':0})
        label=next(label for label in result['topic_labels'] if label['id']=='new')
        self.assertEqual(label['confidence'],'low');self.assertIn('仅定义匹配',label['public_reason']);self.assertIn('Quantum widgets',label['public_reason']);self.assertEqual(catalog,CATALOG);self.assertEqual(topics,TOPICS)
    def test_missing_authored_definition_stays_low_even_with_reference(self):
        refs=[{'title':'Private unrelated title','text':'PRIVATE_SENTINEL Quantum widgets research','topics':['new']}]
        engine=LexicalCandidates(refs,TOPICS,CATALOG);scores,_=engine.score('Quantum widgets public scientific experiment')
        self.assertTrue(scores['new']['cold_start']);self.assertNotIn('PRIVATE',str(scores))
    def test_fallback_is_valid_public_pending_definition(self):
        definition=definition_for_topic(TOPICS[1],{})
        self.assertEqual(definition['definition_status'],'pending');self.assertIn('Scientific methods',definition['definition']);self.assertEqual(definition['include'],['Quantum widgets'])
        catalog=copy.deepcopy(CATALOG);catalog['topics'].append(definition);self.assertIs(validate_catalog(catalog),catalog)
    def test_existing_binding_uses_authored_definition_after_rename(self):
        authored=CATALOG['topics'][0];topic={**TOPICS[0],'name':'Renamed','path':'Renamed','catalog_path':'Scientific methods'}
        self.assertIs(definition_for_topic(topic,{'Scientific methods':authored}),authored)
if __name__=='__main__':unittest.main()
