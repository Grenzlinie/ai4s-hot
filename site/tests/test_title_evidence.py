"""Public-only v2.5 context and title evidence regressions, no model or secrets."""
import copy,hashlib,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import yaml
SITE=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(SITE))
from topics_catalog import load_catalog
from topics_candidates import LexicalCandidates,phrase_hit
from topics_decision import content_facets,decide,DEFAULTS
from topics_schema import validate_archive
import topics_classifier as classifier
CATALOG=load_catalog(SITE/'topics/catalog.yaml')
PATHS={r['path']:'public-'+hashlib.sha256(r['path'].encode()).hexdigest()[:12] for r in CATALOG['topics']}
TOPICS=[{'id':PATHS[r['path']],'name':r['path'].split(' / ')[-1],'path':r['path'],'catalog_path':r['path'],'parent_id':PATHS.get(r['path'].rsplit(' / ',1)[0]) if ' / ' in r['path'] else None} for r in CATALOG['topics']]
def decide_title(title,excerpt='',kind='paper'):
 item={'id':'public','title':title,'excerpt':excerpt,'type':kind,'url':'https://example.org/public'};scores,coverage=LexicalCandidates([],TOPICS,CATALOG).score(title+' '+excerpt)
 return item,decide(item,TOPICS,scores,coverage,[],DEFAULTS)
class TitleEvidence(unittest.TestCase):
 def test_14_technical_acquisition_contexts_are_not_organizations(self):
  phrases=['data acquisition','information acquisition','signal acquisition','knowledge acquisition','image acquisition','feature acquisition','acquisition function','acquisition functions','data-acquisition','signal acquisition strategy','Bayesian acquisition function','active data acquisition','electroencephalogram signal acquisition','data acquisition at Microsoft Research']
  for phrase in phrases:
   with self.subTest(phrase=phrase):self.assertEqual(content_facets({'title':'Scientific materials study','excerpt':phrase,'type':'paper'})[:2],('research','web:paper'))
 def test_real_acquisition_and_appointment_retained(self):
  for title in ['OpenAI acquires an AI startup','Acme announces acquisition of Beta','Company acquisition deal closes','Anthropic appoints new chief scientist','Director appointment at the company']:
   with self.subTest(title=title):self.assertEqual(content_facets({'title':title,'type':'news'})[:2],('non_research','web:organization_policy'))
  self.assertEqual(content_facets({'title':'Optimizing patient appointment scheduling','type':'paper'})[:2],('research','web:paper'))
 def test_empty_and_weak_titles_do_not_infer_leaves(self):
  for title in ['', 'A promising new direction', 'New insight into unknown phenomena']:
   with self.subTest(title=title):self.assertFalse(decide_title(title)[1]['topic_leaf_ids'])
 def test_strong_title_leaf_is_direct_hit_low_confidence_and_public_schema(self):
  item,result=decide_title('Graph neural network for metal-organic framework discovery')
  expected=[PATHS['01 材料研究 / 多孔框架材料'],PATHS['02 AI方法 / 表征、预测与分析 / 图学习与结构表征']]
  self.assertTrue(set(expected)<=set(result['topic_leaf_ids']))
  definitions={PATHS[d['path']]:d for d in CATALOG['topics']}
  for label in result['topic_labels']:
   self.assertTrue(any(phrase_hit(s,item['title']) for s in definitions[label['id']]['include']));self.assertEqual(label['confidence'],'low');self.assertIn('仅依据公开标题',label['public_reason']);self.assertIn('未使用摘要',label['public_reason'])
  validate_archive({'schema_version':2,'taxonomy':{'topics':TOPICS},'items':[{**item,**result}]})
 def test_multi_facet_title_and_root_fallback(self):
  _,multi=decide_title('Graph neural network metal-organic framework experimental dataset')
  self.assertGreaterEqual(len({l['facet'] for l in multi['topic_labels']}),3)
  _,root=decide_title('New chemistry materials research')
  self.assertEqual(root['topic_leaf_ids'],[PATHS['01 材料研究']]);self.assertEqual(root['topic_status'],'broad_only');self.assertEqual(root['topic_labels'][0]['confidence'],'low')
 def test_molecular_biology_and_chemistry_alone_cannot_force_material_root(self):
  for title in ['Molecular biology of protein folding','Clinical molecular imaging study','New chemistry of protein binding','Chemical investigation of living cells']:
   with self.subTest(title=title):
    _,result=decide_title(title);self.assertNotIn(PATHS['01 材料研究'],result['topic_ids'])
 def test_excerpt_similarity_cannot_supply_missing_title_leaf(self):
  item={'title':'Unspecified study','excerpt':'graph neural network','type':'paper'};scores,coverage=LexicalCandidates([],TOPICS,CATALOG).score(item['title']+' '+item['excerpt']);result=decide(item,TOPICS,scores,coverage,[],DEFAULTS);self.assertFalse(result['topic_leaf_ids'])
 def test_release_title_does_not_get_research_labels(self):
  _,result=decide_title('Introducing Graph neural network model','',kind='release');self.assertEqual(result['topic_scope'],'non_research');self.assertFalse(result['topic_leaf_ids']);self.assertEqual(result['content_kind'],'web:model_release')
 def test_empty_corpus_keeps_direct_title_and_version_invalidates_cache(self):
  items=[{'id':'p','title':'Graph neural network for metal-organic framework','excerpt':'','type':'paper','topic_cache_token':'old-v24-token'}];taxonomy={'topics':copy.deepcopy(TOPICS),'version':'synthetic-public'}
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'catalog.yaml').write_text(yaml.safe_dump(CATALOG));(root/'thresholds.yaml').write_text('backend: lexical\ncalibration_status: synthetic\n')
   with patch.object(classifier,'ROOT',root),patch.object(classifier,'load_private_config',return_value={'id_salt':'synthetic-test-salt-not-real'}):
    first=classifier.classify_v2(items,taxonomy,[]);second=classifier.classify_v2(items,taxonomy,[])
  self.assertEqual(first['classified'],1);self.assertEqual(second['classified'],0);self.assertTrue(items[0]['topic_leaf_ids']);self.assertEqual(items[0]['topic_version'],'faceted-local-v2.5');self.assertNotIn('old-v24-token',items[0]['topic_cache_token']);validate_archive({'schema_version':2,'taxonomy':taxonomy,'items':items})
if __name__=='__main__':unittest.main()
