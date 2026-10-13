"""Independent journal archive integration: synthetic metadata, no network or models."""
import argparse,contextlib,copy,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
SITE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SITE))
import collect,enrichment,journals,topics_schema
from build import build
REGISTRY=[{'id':'nature-materials','title':'Nature Materials','issns':['1476-1122','1476-4660'],'publisher':'Springer Nature'}]
def row(ident='journal-new',status='relevant',**overrides):
 return {'id':ident,'title':'Machine learning for crystalline materials','url':'https://www.nature.com/articles/s41563-026-00123-4','doi':'10.1038/s41563-026-00123-4','first_seen':collect.NOW.isoformat(),'published_at':'2026-10-01T00:00:00+00:00','group':'papers','groups':['papers'],'type':'paper','excerpt':'Public material machine learning abstract','source_ids':['journal-nature-materials'],'source_names':['Nature Materials'],'tags':[],'journal_id':'nature-materials','journal_title':'Nature Materials','journal_issns':['1476-1122','1476-4660'],'publisher':'Springer Nature','published_online_at':'2026-10-01T00:00:00+00:00','published_print_at':None,'indexed_at':collect.NOW.isoformat(),'journal_relevance':{'status':status,'method':'rule-v1','reason':'Public title and abstract screening','version':journals.relevance('Machine learning for materials','Public abstract')['version']},**overrides}
def payload(rows=None):return {'schema_version':2,'generated_at':collect.NOW.isoformat(),'items':rows if rows is not None else [row()],'sources':[],'journals':copy.deepcopy(REGISTRY),'taxonomy':{'topics':[],'status':'ok','identity_version':'hmac-v1'}}
class JournalIntegration(unittest.TestCase):
 def test_doi_exact_normalized_cross_provider_preserves_id_and_first_seen(self):
  old=row('bookmarked-id',doi=' HTTPS://DOI.ORG/10.1038/S41563-026-00123-4 ',first_seen='2026-09-01T00:00:00+00:00',source_ids=['rss'])
  incoming=row('api-different-id',doi='doi: 10.1038/s41563-026-00123-4',source_ids=['crossref']);state={old['id']:old};collect.merge(state,[incoming,copy.deepcopy(incoming)])
  self.assertEqual(list(state),['bookmarked-id']);self.assertEqual(old['first_seen'],'2026-09-01T00:00:00+00:00');self.assertEqual(old['doi'],'10.1038/s41563-026-00123-4');self.assertEqual(set(old['source_ids']),{'rss','crossref'})
  different=row('not-same',doi='10.1038/s41563-026-00123-40');collect.merge(state,[different]);self.assertEqual(len(state),2)
 def test_first_journal_merge_onto_nonjournal_preserves_explicit_null_dates(self):
  original=row('bookmarked-before-journal',first_seen='2026-09-01T00:00:00+00:00',source_ids=['alphaxiv'])
  for field in ('journal_id','journal_title','journal_issns','publisher','published_online_at','published_print_at','indexed_at','journal_relevance'):original.pop(field)
  incoming=row(published_print_at=None,indexed_at=None);state={original['id']:original};collect.merge(state,[incoming]);self.assertEqual(list(state),['bookmarked-before-journal']);self.assertEqual(original['first_seen'],'2026-09-01T00:00:00+00:00');self.assertIn('published_print_at',original);self.assertIsNone(original['published_print_at']);self.assertIn('indexed_at',original);self.assertIsNone(original['indexed_at']);topics_schema.validate_archive(payload([original]))
 def test_doi_url_encoded_identity_without_explicit_field(self):
  original=row('saved',doi=None,url='https://doi.org/10.1038%2FS41563-026-00123-4');state={'saved':original};collect.merge(state,[row()]);self.assertEqual(list(state),['saved'])
 def test_registry_and_public_journal_fields_fail_closed(self):
  valid=payload();topics_schema.validate_archive(valid)
  mutators=[lambda p:p['journals'][0].update(private_key='SECRET'),lambda p:p['journals'].append(copy.deepcopy(p['journals'][0])),lambda p:p['items'][0].update(private_reference='SECRET'),lambda p:p['items'][0].update(journal_id='other'),lambda p:p['items'][0].update(journal_title='Wrong title'),lambda p:p['items'][0].update(journal_issns=['1234-5678']),lambda p:p['items'][0]['journal_relevance'].update(private_score='SECRET'),lambda p:p['items'][0].update(published_online_at='not-a-date'),lambda p:p['items'][0].update(indexed_at='2026-10-13T00:00:00'),lambda p:p['items'][0].pop('publisher')]
  for i,mutate in enumerate(mutators):
   with self.subTest(boundary=i):
    bad=copy.deepcopy(valid);mutate(bad)
    with self.assertRaises(ValueError):topics_schema.validate_archive(bad)
 def execute(self,tmp,stage=None,provider_status='ok'):
  root=Path(tmp);data=root/'data';data.mkdir();index=data/'index.json';index.write_text(json.dumps(payload([])));ledger=data/'journal-state.json';ledger.write_text('{"version":1,"journals":{},"marker":"old"}');config=root/'sources.json';config.write_text(json.dumps({'journals_config':'journals.json','sources':[],'lookback_days':30,'max_items_per_source':12,'summary_budget':4}));(root/'journals.json').write_text('{}')
  before=(index.read_bytes(),ledger.read_bytes());items=[row('relevant'),row('pending',status='pending',doi='10.1038/s41563-026-00999-0',url='https://www.nature.com/articles/s41563-026-00999-0')];statuses=[{'id':'journal-nature-materials','name':'Nature Materials','status':provider_status,'count':2}];new_state={'version':1,'journals':{'nature-materials':{'records':{}}}};taxonomy={'topics':[],'identity_version':'hmac-v1','status':'stale' if stage=='taxonomy' else 'ok'}
  env={'TOPICS_MODE':'v2','OPENAI_API_KEY':'synthetic','OPENAI_API_BASE':'https://mock.invalid'}
  with patch.dict(os.environ,env,clear=True),patch.object(journals,'collect',return_value=(items,statuses,copy.deepcopy(REGISTRY),new_state)),patch.object(collect.site_topics,'read_taxonomy',return_value=(taxonomy,[])),patch.object(collect.site_topics,'classify',return_value={'status':'ok','classified':0,'unclassified':2}),patch.object(collect,'summary_config',return_value='synthetic'),patch.object(collect,'summarize',return_value={'status':'ok','generated':0}) as summary,patch.object(enrichment,'enrich',return_value=({}, {'status':'ok'})) as enrich,patch.object(enrichment,'settings',return_value={**enrichment.DEFAULTS,'enabled':True}),patch.object(collect.requests,'get',side_effect=AssertionError('Network forbidden')),contextlib.redirect_stdout(io.StringIO()):
   ctx=patch.object(topics_schema,'validate_archive',side_effect=ValueError('Synthetic validation failure')) if stage=='validation' else contextlib.nullcontext()
   with ctx:
    if stage:
     with self.assertRaises(collect.UpdateFailure) as caught:collect.run(argparse.Namespace(config=config,data_dir=data,paper_export=None,source=None,no_summary=False,summary_budget=4))
     self.assertEqual(caught.exception.stage,stage);summary.assert_not_called();enrich.assert_not_called();self.assertEqual((index.read_bytes(),ledger.read_bytes()),before);self.assertFalse((data/'daily').exists())
    else:
     collect.run(argparse.Namespace(config=config,data_dir=data,paper_export=None,source=None,no_summary=False,summary_budget=4));self.assertEqual([p['id'] for p in summary.call_args.args[0]],['relevant']);self.assertEqual([p['id'] for p in enrich.call_args.args[0]],['relevant']);archived=json.loads(index.read_text());self.assertEqual({p['id'] for p in archived['items']},{'relevant','pending'});self.assertEqual(json.loads(ledger.read_text()),new_state)
 def test_pending_browsable_but_no_summary_or_enrichment(self):
  with tempfile.TemporaryDirectory() as tmp:self.execute(tmp)
 def test_partial_journal_coverage_with_usable_rows_can_publish(self):
  with tempfile.TemporaryDirectory() as tmp:self.execute(tmp,provider_status='partial')
 def test_late_doi_after_pii_leaves_rss_keeps_original_identity(self):
  from test_journals import JOURNAL,NOW,entry,rss,crossref
  pii='https://www.sciencedirect.com/science/article/pii/S1359645426000012'
  with tempfile.TemporaryDirectory() as tmp:
   cfg,path=Path(tmp)/'config.json',Path(tmp)/'state.json';cfg.write_text(json.dumps({'journals':[JOURNAL]}))
   with patch.object(journals,'_get',return_value=b'RSS'),patch.object(journals.feedparser,'parse',return_value=rss([entry(link=pii)])),patch.object(journals,'_crossref',return_value=([],[])):first,_,_,state=journals.collect(cfg,path,NOW)
   path.write_text(json.dumps(state))
   with patch.object(journals,'_get',return_value=b'RSS'),patch.object(journals.feedparser,'parse',return_value=rss([])),patch.object(journals,'_crossref',return_value=([journals._crossref_record(crossref())],[])):second,_,_,_=journals.collect(cfg,path,NOW.replace(day=14))
  self.assertEqual(len(second),1);self.assertEqual(second[0]['id'],first[0]['id']);self.assertEqual(second[0]['first_seen'],first[0]['first_seen']);self.assertEqual(second[0]['doi'],'10.1234/test1')
 def test_same_doi_screening_update_is_one_article_not_two_states(self):
  original=row('bookmarked',status='relevant',first_seen='2026-09-01T00:00:00+00:00');state={'bookmarked':original};collect.merge(state,[row('different-provider-id',status='pending')]);self.assertEqual(list(state),['bookmarked']);self.assertEqual(original['journal_relevance']['status'],'pending');self.assertEqual(original['first_seen'],'2026-09-01T00:00:00+00:00')
 def test_taxonomy_failure_preserves_journal_state_and_index(self):
  with tempfile.TemporaryDirectory() as tmp:self.execute(tmp,'taxonomy')
 def test_validation_failure_preserves_journal_state_and_index(self):
  with tempfile.TemporaryDirectory() as tmp:self.execute(tmp,'validation')
 def test_excluded_removes_old_pending_but_preserves_other_provider_identity(self):
  excluded=row('former-pending',status='excluded');state={'journals':{'nature-materials':{'records':{'doi-key':excluded}}}}
  only=row('only-journal',status='pending');mixed=row('saved-multi-source',status='pending',source_ids=['journal-nature-materials','alphaxiv'],source_names=['Nature Materials','alphaXiv'])
  items={'only-journal':only,'saved-multi-source':mixed};collect.reconcile_journal_decisions(items,state)
  self.assertNotIn('only-journal',items);self.assertEqual(list(items),['saved-multi-source']);self.assertEqual(mixed['source_ids'],['alphaxiv']);self.assertNotIn('journal_id',mixed);self.assertNotIn('journal_relevance',mixed);self.assertEqual(mixed['first_seen'],collect.NOW.isoformat())
 def test_build_never_copies_candidate_cache_even_reused_output(self):
  with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
   root=Path(tmp);data=root/'data';out=root/'output';data.mkdir();(data/'index.json').write_text(json.dumps(payload()));(data/'journal-state.json').write_text('SECRET_CANDIDATE');(out/'data').mkdir(parents=True);(out/'data/journal-state.json').write_text('OLD_CANDIDATE');build(data,out);self.assertFalse((out/'data/journal-state.json').exists());self.assertNotIn('SECRET_CANDIDATE',''.join(p.read_text() for p in out.rglob('*.json')))
if __name__=='__main__':unittest.main()
