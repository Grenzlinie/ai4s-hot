"""Independent v2 contracts. Synthetic inputs; no Zotero/model/network access."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

SITE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SITE))
from topics_corpus import prepare,exact_match
from topics_candidates import LexicalCandidates
from topics_decision import decide,DEFAULTS,content_facets
import topics_classifier as classifier
import topics_semantic

CATALOG=yaml.safe_load((SITE/'topics/catalog.yaml').read_text())
TOPICS=[]
PATH_IDS={row['path']:'test-'+str(n) for n,row in enumerate(CATALOG['topics'])}
for row in CATALOG['topics']:
    path=row['path']; parent=path.rsplit(' / ',1)[0] if ' / ' in path else None
    TOPICS.append({'id':PATH_IDS[path],'name':path.split(' / ')[-1],'path':path,'parent_id':PATH_IDS.get(parent),'active':True})
ENV={'ZOTERO_TOPIC_CONFIG':json.dumps({'id_salt':'SYNTHETIC_PRIVATE_SALT_0123456789abcdef','publish_root_keys':['synthetic-root']})}


def topic(name):return next(t['id'] for t in TOPICS if t['name']==name)
def paper(title,excerpt,**extra):return {'id':'public-item','title':title,'excerpt':excerpt,'url':'https://example.test/article','type':'paper',**extra}
def lexical(item,corpus=None,topics=TOPICS):
    engine=LexicalCandidates(corpus or [],topics,CATALOG)
    scores,coverage=engine.score(item['title']+' '+item['excerpt'])
    return decide(item,topics,scores,coverage,[],DEFAULTS)


class V2CoreAcceptance(unittest.TestCase):
    def test_t03_two_facets_survive_independent_selection(self):
        result=lexical(paper('MOF with a machine learning potential','This research measures gas adsorption in a metal-organic framework using an interatomic potential and molecular simulations.'))
        self.assertIn(topic('多孔框架材料'),result['topic_ids'])
        self.assertIn(topic('机器学习势函数'),result['topic_ids'])

    def test_t04_residual_diagnosis_does_not_imply_bayesian_optimization(self):
        result=lexical(paper('Photoemission residual diagnosis','This research scans exponents and measures residual uncertainty of photoemission yields without proposing any next experimental sample.'))
        self.assertNotIn(topic('主动学习与贝叶斯优化'),result['topic_ids'])

    def test_t05_organization_and_actual_release_type_are_not_papers(self):
        scope,kind,_=content_facets(paper('Barclays partnership','Bank enterprise deployment of Claude Code for employees.',type='report'))
        self.assertEqual((scope,kind),('non_research','web:organization_policy'))
        scope,kind,_=content_facets(paper('Qwen/Qwen3-8B','Official model repository for inference.',type='release'))
        self.assertEqual((scope,kind),('non_research','web:model_release'))

    def test_t06_definition_only_topic_has_cold_start_path(self):
        result=lexical(paper('MOF gas adsorption','This research studies a metal-organic framework for gas adsorption across a range of temperatures and pressures.'))
        self.assertIn(topic('多孔框架材料'),result['topic_ids'])
        label=next(row for row in result['topic_labels'] if row['id']==topic('多孔框架材料'))
        self.assertEqual(label['confidence'],'low')
        self.assertIn('仅定义匹配',label['public_reason'])

    def test_t07_oov_music_festival_rejects_crystal_word_overlap(self):
        result=lexical(paper('Crystal music festival','Jazz trumpet improvisation concert fashion jewellery tickets entertainment celebration audience orchestra.',type='report'))
        self.assertEqual(result['topic_ids'],[])

    def test_t08_insufficient_abstract_is_distinguished(self):
        result=lexical(paper('Unclear scientific report',''))
        self.assertEqual(result['topic_status'],'insufficient_evidence')

    def test_t09_identity_conflict_does_not_inherit_labels(self):
        corpus=prepare([{'title':'Same title','text':'reference','doi':'10.1234/one','topics':['a']}])
        self.assertEqual(exact_match({'title':'Same title','doi':'10.1234/two'},corpus),[])

    def test_reference_identity_deduplicates_shared_doi_with_optional_arxiv(self):
        corpus=prepare([
            {'title':'One','text':'reference','doi':'10.1234/same','arxiv_id':'2609.12345','topics':['a']},
            {'title':'One','text':'reference','doi':'10.1234/same','topics':['b']},
        ])
        self.assertEqual(len(corpus),1)
        self.assertEqual(set(corpus[0]['topics']),{'a','b'})

    def test_t10_duplicate_equal_length_reference_order_is_stable(self):
        corpus=[
            {'title':'Same title','text':'crystal','doi':'10.1234/shared','topics':['a']},
            {'title':'Same title','text':'protein','doi':'10.1234/shared','topics':['b']},
        ]
        self.assertEqual(prepare(corpus),prepare(list(reversed(corpus))))

    def test_definition_binding_survives_display_rename(self):
        renamed=copy.deepcopy(TOPICS)
        node=next(t for t in renamed if t['id']==topic('多孔框架材料'))
        node['catalog_path']=node['path'];node['path']='01 材料研究 / Renamed porous research';node['name']='Renamed porous research'
        result=lexical(paper('MOF gas adsorption','This research studies a metal-organic framework for gas adsorption across a range of temperatures and pressures.'),topics=renamed)
        self.assertIn(node['id'],result['topic_ids'])

    def run_classifier(self,root,items,corpus,**kwargs):
        taxonomy={'topics':copy.deepcopy(TOPICS),'version':'test-taxonomy'}
        with patch.dict(classifier.os.environ,ENV),patch.object(classifier,'ROOT',root):
            status=classifier.classify_v2(items,taxonomy,corpus,**kwargs)
        return status,taxonomy

    def root(self,directory,backend='lexical'):
        root=Path(directory)
        (root/'catalog.yaml').write_text(yaml.safe_dump(CATALOG,allow_unicode=True))
        (root/'thresholds.yaml').write_text(yaml.safe_dump({'backend':backend,'calibration_status':'unvalidated'}))
        return root

    def test_t10_cache_versions_thresholds_and_order_are_auditable(self):
        corpus=[{'title':'Reference one','text':'crystal material PRIVATE_SENTINEL','topics':[topic('多孔框架材料')]},{'title':'Reference two','text':'potential force field','topics':[topic('机器学习势函数')]}]
        items=[paper('MOF interatomic potential','A research study examines gas adsorption using an interatomic potential and metal-organic framework simulations.')]
        with tempfile.TemporaryDirectory() as tmp:
            root=self.root(tmp)
            self.assertEqual(self.run_classifier(root,items,corpus)[0]['classified'],1)
            token=items[0]['topic_cache_token']
            self.assertEqual(self.run_classifier(root,items,list(reversed(corpus)))[0]['classified'],0)
            (root/'thresholds.yaml').write_text(yaml.safe_dump({'backend':'lexical','calibration_status':'unvalidated','min_score':.27}))
            self.assertEqual(self.run_classifier(root,items,corpus)[0]['classified'],1)
            self.assertNotEqual(token,items[0]['topic_cache_token'])
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(items))

    def test_t11_semantic_dependency_failure_reports_degraded(self):
        items=[paper('MOF research','A research study examines gas adsorption in a metal-organic framework with molecular simulations.')]
        corpus=[{'title':'Example','text':'gas adsorption MOF','topics':[topic('多孔框架材料')]}]
        with tempfile.TemporaryDirectory() as tmp,patch.object(topics_semantic,'SemanticCandidates',side_effect=ImportError('synthetic missing dependency')):
            result,_=self.run_classifier(self.root(tmp,'fusion'),items,corpus)
        self.assertEqual(result['status'],'degraded')
        self.assertEqual(items[0]['topic_backend'],'degraded_lexical')

    def test_t12_public_receipt_never_contains_private_reference(self):
        items=[paper('MOF research','A research study examines gas adsorption in a metal-organic framework with molecular simulations.')]
        corpus=[{'title':'PRIVATE_REFERENCE','text':'PRIVATE_ABSTRACT MOF crystal material','topics':[topic('多孔框架材料')],'private_key':'PRIVATE_KEY'}]
        with tempfile.TemporaryDirectory() as tmp:
            status,taxonomy=self.run_classifier(self.root(tmp),items,corpus)
        self.assertNotIn('PRIVATE',json.dumps({'items':items,'taxonomy':taxonomy,'status':status}))


if __name__=='__main__':unittest.main()
