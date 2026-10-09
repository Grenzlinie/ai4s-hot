import copy, os, pathlib, sys, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from topics_evaluate import canonical_id, evaluate, leakage_check, split_records, validate_gold
T={'topics':[{'id':'r','parent_id':None},{'id':'a','parent_id':'r'},{'id':'b','parent_id':'r'}]}
def gold(labels=None,scope='research',broad=False):
    return dict(human_confirmed=True,reviewer='Test reviewer',reviewed_at='2026-10-09T00:00:00Z',scope=scope,content_kind='paper',domain_facets=['web:materials'],acceptable_topic_sets=[labels if labels is not None else ['a']],fine_applicable=not broad,status='broad_only' if broad else 'classified',public_reason='Synthetic fixture only, not production gold.')
def row(ident='1',g=None):return {'id':ident,'canonical_id':'url:https://example.org/'+ident,'split':'holdout','item':{'id':ident,'url':'https://example.org/'+ident,'title':'Title '+ident},'gold':g or gold()}
def pred(ident='1',labels=None):return {'id':ident,'topic_leaf_ids':labels if labels is not None else ['a'],'content_kind':'paper','domain_facets':['web:materials']}
class EvaluationTests(unittest.TestCase):
    def test_canonical_versions(self):
        self.assertEqual(canonical_id({'url':'http://arxiv.org/abs/2601.12345v2'}),canonical_id({'url':'https://arxiv.org/pdf/2601.12345v3'}))
        self.assertEqual(canonical_id({'url':'https://doi.org/10.1234/ABC'}),'doi:10.1234/abc')
    def test_audited_groups_never_holdout(self):
        items=[row()['item']];records=split_records(items,items+[row('2')['item']]);self.assertEqual(len(records),2);self.assertEqual(sum(r['split']=='holdout' for r in records),1)
    def test_no_candidate_gold(self):
        g=gold();g['human_confirmed']=False
        with self.assertRaises(ValueError):validate_gold(g,T)
    def test_parent_not_fine_credit(self):
        result=evaluate([row()],[pred(labels=['r'])],T,bootstrap=10)
        self.assertEqual(result['metrics']['fine']['fn'],1);self.assertEqual(result['metrics']['root']['tp'],1)
    def test_nonresearch_false_positive(self):
        g=gold([],scope='non_research');result=evaluate([row(g=g)],[pred()],T,bootstrap=10)
        self.assertEqual(result['metrics']['fine']['fp'],1);self.assertEqual(result['metrics']['nonresearch_leak'],1)
    def test_broad_separate(self):
        result=evaluate([row(g=gold(['r'],broad=True))],[pred()],T,bootstrap=10)
        self.assertEqual(result['metrics']['fine_n'],0);self.assertEqual(result['metrics']['broad_overspecific'],1)
    def test_alternative_full_set(self):
        g=gold();g['acceptable_topic_sets']=[['a'],['b']];result=evaluate([row(g=g)],[pred(labels=['b'])],T,bootstrap=10)
        self.assertEqual(result['metrics']['fine']['f1'],1)
    def test_fails_closed_external_and_support(self):
        result=evaluate([row()],[pred()],T,baseline_f1=.5,bootstrap=10)
        self.assertFalse(result['quality_pass']);self.assertFalse(result['gates']['holdout_n']);self.assertFalse(result['gates']['private_exclusion_verified'])
    def test_privacy_leak_counts_only(self):
        refs=[{'url':'https://example.org/private','title':'Title 1','PRIVATE_MARKER':'Never publish'}]
        result=leakage_check([row()],refs,{'1'})
        self.assertEqual(result['private_reference_overlap'],1);self.assertEqual(result['override_overlap'],1);self.assertNotIn('PRIVATE_MARKER',str(result))
    def test_unknown_gold_id_rejected(self):
        with self.assertRaises(ValueError):validate_gold(gold(['unknown']),T)
    def test_missing_predictions_rejected(self):
        with self.assertRaises(ValueError):evaluate([row()],[],T)
    def test_unconfirmed_dataset_rejected(self):
        r=row();r['gold']=None
        with self.assertRaises(ValueError):evaluate([r],[pred()],T)
    def test_duplicate_ancestor_gold_rejected(self):
        with self.assertRaises(ValueError):validate_gold(gold(['r','a']),T)
if __name__=='__main__':unittest.main()

class AliasGroupingTests(unittest.TestCase):
    def test_doi_arxiv_bridge_keeps_entire_group_dev(self):
        a={'id':'a','url':'https://doi.org/10.1234/one','title':'Published title'}
        b={'id':'b','url':'https://arxiv.org/abs/2601.12345','doi':'10.1234/one','title':'Preprint title'}
        c={'id':'c','url':'https://arxiv.org/abs/2601.12345v2','title':'New title'}
        rows=split_records([a],[b,c]);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['split'],'dev')

class ReferenceExclusionTests(unittest.TestCase):
    def test_title_only_private_reference_excluded_in_memory(self):
        from topics_evaluate import exclude_holdout_references
        references=[{'title':'Title 1','text':'PRIVATE_MARKER'},{'title':'Other reference','text':'PRIVATE_OTHER'}]
        kept,receipt=exclude_holdout_references([row()],references)
        self.assertEqual(len(kept),1);self.assertEqual(receipt['excluded_holdout_reference_n'],1);self.assertNotIn('PRIVATE',str(receipt))
    def test_doi_alias_excluded(self):
        from topics_evaluate import exclude_holdout_references
        r=row();r['item']['doi']='10.1234/abc'
        kept,_=exclude_holdout_references([r],[{'url':'https://doi.org/10.1234/abc','title':'Different title'}]);self.assertFalse(kept)

class AdapterTests(unittest.TestCase):
    def test_web_contract_adapter(self):
        from topics_evaluate import adapt_prediction
        p=adapt_prediction({'id':'1','content_kind':'web:technical_report','topic_scope':'research','topic_status':'broad_only'})
        self.assertEqual(p['content_kind'],'technicalreport');self.assertEqual(p['scope'],'research');self.assertEqual(p['status'],'broad_only')
    def test_alias_alignment_does_not_mutate_original(self):
        from topics_evaluate import align_dataset_taxonomy
        d={'records':[row()], 'taxonomy':T};new={'topics':[{'id':'new','parent_id':None}],'aliases':{'a':'new'}}
        aligned=align_dataset_taxonomy(d,new);self.assertEqual(aligned['records'][0]['gold']['acceptable_topic_sets'],[['new']]);self.assertEqual(d['records'][0]['gold']['acceptable_topic_sets'],[['a']])

class SafePredictionTests(unittest.TestCase):
    def test_holdout_reference_and_override_removed_before_core(self):
        import importlib.util
        from unittest.mock import patch
        script=pathlib.Path(__file__).resolve().parents[2]/'scripts/predict_evaluation.py'
        spec=importlib.util.spec_from_file_location('safe_prediction',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data={'taxonomy':T,'records':[row()]}; refs=[{'title':'Title 1','text':'PRIVATE_SENTINEL','topics':['a']}]
        def core(items,taxonomy,corpus,**kwargs):
            self.assertEqual(corpus,[]);self.assertEqual(kwargs['overrides_payload']['overrides'],[])
            self.assertNotIn('gold',items[0]);items[0].update(content_kind='web:paper',topic_scope='research',topic_status='classified',topic_leaf_ids=['a']);return {'algorithm':'fixture'}
        with patch.dict(os.environ),patch('site_topics.read_taxonomy',return_value=({**T,'status':'ok'},refs)),patch('topics_classifier.classify_v2',side_effect=core):
            predictions,receipt,_=module.predict(data,'holdout','v2',{'schema_version':1,'overrides':[{'item_id':'1','topic_ids':['a']}]})
        self.assertEqual(receipt['reference_exclusion']['excluded_holdout_reference_n'],1);self.assertEqual(receipt['holdout_override_excluded_n'],1);self.assertNotIn('PRIVATE',str(predictions)+str(receipt))

class GoldBoundaryTests(unittest.TestCase):
    def test_nonresearch_cannot_escape_false_positive_denominator(self):
        g=gold([],scope='non_research');g['fine_applicable']=False
        with self.assertRaises(ValueError):validate_gold(g,T)
    def test_only_research_broad_can_disable_fine(self):
        for scope,status in [('research','classified'),('unknown','insufficient_evidence'),('non_research','broad_only')]:
            g=gold([],scope=scope);g.update(fine_applicable=False,status=status)
            with self.subTest(scope=scope,status=status),self.assertRaises(ValueError):validate_gold(g,T)
    def test_abstention_states_require_empty_research_labels(self):
        for status in ('insufficient_evidence','taxonomy_gap'):
            g=gold();g['status']=status
            with self.subTest(status=status),self.assertRaises(ValueError):validate_gold(g,T)
            g['acceptable_topic_sets']=[[]];self.assertEqual(validate_gold(g,T),g)
    def test_broad_only_requires_nonempty_parent(self):
        for labels in ([],['a']):
            with self.assertRaises(ValueError):validate_gold(gold(labels,broad=True),T)
    def test_iso_timezone_required(self):
        for value in ('not-a-date','2026-10-09','2026-10-09T00:00:00',' ',None):
            g=gold();g['reviewed_at']=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate_gold(g,T)
        for value in ('2026-10-09T00:00:00Z','2026-10-09T08:00:00+08:00'):
            g=gold();g['reviewed_at']=value;self.assertEqual(validate_gold(g,T),g)
    def test_domain_catalog_whitelist_and_duplicates(self):
        for labels in (['web:invented'],['web:materials','web:materials']):
            g=gold();g['domain_facets']=labels
            with self.assertRaises(ValueError):validate_gold(g,T)
        import yaml
        from topics_evaluate import DOMAIN_FACETS
        catalog=yaml.safe_load((pathlib.Path(__file__).resolve().parents[1]/'topics/catalog.yaml').read_text())
        self.assertEqual(DOMAIN_FACETS,set(catalog['web_facets']['domain']))
    def test_private_exclusion_receipt_cannot_be_reused_for_other_predictions(self):
        from topics_evaluate import digest,verify_external_receipts,adapt_prediction
        dataset={'records':[row()]};predictions=[pred()]
        evidence={'private_exclusion_verified':{'dataset_sha256':digest(dataset),'predictions_sha256':digest([adapt_prediction(p) for p in predictions]),'reviewer':'Independent reviewer','pass':True},'independent_review_verified':{'dataset_sha256':digest(dataset),'reviewer':'Independent reviewer','pass':True}}
        self.assertTrue(verify_external_receipts(evidence,dataset,predictions)['private_exclusion_verified'])
        other=[pred(labels=['b'])];self.assertFalse(verify_external_receipts(evidence,dataset,other)['private_exclusion_verified'])
        evidence['private_exclusion_verified'].pop('predictions_sha256');self.assertFalse(verify_external_receipts(evidence,dataset,predictions)['private_exclusion_verified'])

class SharedIdentityBaselineTests(unittest.TestCase):
    def test_v1_filters_different_title_same_doi_before_classification(self):
        import importlib.util,os
        from unittest.mock import patch
        script=pathlib.Path(__file__).resolve().parents[2]/'scripts/predict_evaluation.py'
        spec=importlib.util.spec_from_file_location('shared_identity_baseline',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        record=row();record['item']['doi']='10.1234/shared'
        dataset={'taxonomy':T,'records':[record]}
        refs=[{'title':'Different private published title','doi':'10.1234/shared','text':'PRIVATE_SENTINEL','topics':['a']},{'title':'Unrelated private reference','doi':'10.1234/other','text':'UNRELATED_PRIVATE','topics':['a']}]
        def reader(*args):
            self.assertEqual(os.environ['TOPICS_MODE'],'v2')
            return {**T,'status':'ok','version':'stable-fixture'},refs
        def baseline(items,taxonomy,corpus):
            self.assertEqual(taxonomy['version'],'stable-fixture');self.assertEqual(len(corpus),1);self.assertEqual(corpus[0]['doi'],'10.1234/other')
            self.assertNotIn('gold',items[0]);items[0].update(topic_leaf_ids=[]);return {'status':'ok'}
        with patch.dict(os.environ,{'TOPICS_MODE':'v1'}),patch('site_topics.read_taxonomy',side_effect=reader),patch('topics_v1.classify',side_effect=baseline):
            predictions,receipt,_=module.predict(dataset,'holdout','v1')
            self.assertEqual(os.environ['TOPICS_MODE'],'v1')
        self.assertEqual(receipt['reference_exclusion']['excluded_holdout_reference_n'],1);self.assertEqual(receipt['training_reference_n'],1);self.assertEqual(receipt['taxonomy_reader'],'v2_shared_identity');self.assertNotIn('PRIVATE',str(receipt)+str(predictions))

class StrictArxivIdentityTests(unittest.TestCase):
    def test_doi_numeric_suffix_is_not_arxiv_and_does_not_merge(self):
        from topics_corpus import identities,prepare
        from topics_evaluate import identity_aliases
        items=[{'id':str(i),'url':f'https://doi.org/10.{i}/2026.12345','doi':f'10.{i}/2026.12345','title':f'Different title {i}','text':'Synthetic private fixture','topics':['a']} for i in (1234,5678)]
        for item in items:
            self.assertNotIn('arxiv',identities(item));self.assertTrue(canonical_id(item).startswith('doi:'));self.assertFalse(any(alias.startswith('arxiv:') for alias in identity_aliases(item)))
        self.assertEqual(len(prepare(items)),2);self.assertEqual(len(split_records([items[0]],[items[1]])),2)
    def test_explicit_arxiv_fields_urls_and_extra_are_accepted(self):
        from topics_corpus import identities
        from topics_evaluate import identity_aliases
        examples=[{'arxiv_id':'2601.12345'},{'arxiv_id':'2601.12345v2'},{'url':'https://arxiv.org/abs/2601.12345v3'},{'url':'http://arxiv.org/pdf/2601.12345v2.pdf'},{'extra':'arXiv: 2601.12345v5'},{'extra':'arXiv ID: 2601.12345v6'}]
        for fields in examples:
            item={'url':'https://example.org/paper','title':'Synthetic public fixture',**fields}
            with self.subTest(fields=fields):
                self.assertEqual(identities(item).get('arxiv'),'2601.12345');self.assertEqual(canonical_id(item),'arxiv:2601.12345');self.assertIn('arxiv:2601.12345',identity_aliases(item))
    def test_unmarked_numbers_and_lookalike_domains_are_not_arxiv(self):
        from topics_corpus import identities
        for fields in ({'url':'https://example.org/2601.12345'},{'extra':'Dataset 2601.12345 version 2'},{'url':'https://notarxiv.org/abs/2601.12345'},{'url':'https://example.org/arxiv.org/abs/2601.12345'}):
            self.assertNotIn('arxiv',identities(fields))
