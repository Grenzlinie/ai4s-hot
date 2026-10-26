"""Independent metadata recovery across journal collection and publication boundaries."""
import argparse,contextlib,copy,io,json,os,sys,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
SITE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SITE))
import journals as j,journal_metadata as m,collect,topics_schema
NOW=datetime(2026,10,26,6,tzinfo=timezone.utc)
J={'id':'nature-materials','title':'Nature Materials','issns':['1476-4660'],'publisher':'Springer Nature','rss':'https://www.nature.com/nmat.rss'}
POSITIVE='Machine learning predicts mechanical properties of alloys and designs new materials through validated experiments. '*3
PENDING='These machine learning materials systems are considered as separate broad topics without an established relationship. '*3
NEGATIVE='Atomistic alloy structures reveal metallic lattice arrangements and conventional physical observations with no statistical models. '*3
def record(n=1,title='Machine learning materials'):
 return {'title':title,'doi':'10.1038/test'+str(n),'url':'https://doi.org/10.1038/test'+str(n),'abstract':'','first_seen':'2026-10-20T00:00:00+00:00','item_id':'original-'+str(n),'journal_relevance':j.relevance(title),'published_online_at':'2026-10-20T00:00:00+00:00','article_type':'journal-article'}
def state(rows=None,used=7):return {'version':1,'metadata_budget':{'date':'2026-10-26','requests':used},'journals':{J['id']:{'records':rows or {'10.1038/test1':record()}}}}
def adapter(journal,old,settings,now):
 block=copy.deepcopy(old);rows=[j._public_item(r,journal,now) for r in block['records'].values()];return rows,{'id':'journal-'+journal['id'],'name':journal['title'],'url':journal['rss'],'status':'ok','count':len(rows),'counters':{'pending':len(rows),'fetched':0}},block
class MetadataIntegration(unittest.TestCase):
 def configs(self,tmp,metadata=True):
  cfg=Path(tmp)/'journals.json';config={'journals':[J]}
  if metadata is not None:config['metadata']={'enabled':metadata,'max_requests':20,'max_candidates':10}
  cfg.write_text(json.dumps(config));return cfg
 def test_previous_daily_budget_survives_collect_and_prevents_next_run_requests(self):
  with tempfile.TemporaryDirectory() as tmp:
   cfg=self.configs(tmp);path=Path(tmp)/'state.json';path.write_text(json.dumps(state(used=19)))
   def missing(doi,title,budget):budget.reserve();return None,None
   with patch.object(j,'_journal',side_effect=adapter),patch.object(m,'_crossref',side_effect=missing) as request,patch.object(m.requests,'Session',side_effect=AssertionError('Network forbidden')):
    _,_,_,first=j.collect(cfg,path,NOW);self.assertEqual(request.call_count,1);self.assertEqual(first['metadata_budget']['requests'],20)
    first['journals'][J['id']]['records']['10.1038/test2']=record(2);path.write_text(json.dumps(first));request.reset_mock();_,_,_,second=j.collect(cfg,path,NOW);request.assert_not_called();self.assertEqual(second['metadata_budget']['requests'],20)
 def test_corrupt_previous_budget_date_cannot_grant_a_fresh_daily_allowance(self):
  bad=state(used=20);bad['metadata_budget']['date']='0000-bad'
  with tempfile.TemporaryDirectory() as tmp:
   cfg=self.configs(tmp);path=Path(tmp)/'state.json';path.write_text(json.dumps(bad));before=path.read_bytes()
   with patch.object(j,'_journal',side_effect=adapter),patch.object(m,'_crossref',return_value=(POSITIVE,None)) as request:_,_,_,updated=j.collect(cfg,path,NOW)
   request.assert_not_called();self.assertEqual(path.read_bytes(),before);self.assertEqual(updated['metadata_budget'],bad['metadata_budget']);self.assertEqual(updated['metadata_recovery']['status'],'budget_invalid')
 def test_recovered_abstract_rescreens_public_rows_health_and_stable_identity(self):
  records={'10.1038/test1':record(1),'10.1038/test2':record(2),'10.1038/test3':record(3,'Atomistic alloy structures')}
  abstracts={'10.1038/test1':POSITIVE,'10.1038/test2':PENDING,'10.1038/test3':NEGATIVE}
  def recovery(doi,title,budget):budget.reserve();return abstracts[doi],None
  with tempfile.TemporaryDirectory() as tmp:
   cfg=self.configs(tmp);path=Path(tmp)/'state.json';path.write_text(json.dumps(state(records)));before=path.read_bytes()
   with patch.object(j,'_journal',side_effect=adapter),patch.object(m,'_crossref',side_effect=recovery),patch.object(m.requests,'Session',side_effect=AssertionError('Network forbidden')):items,health,_,updated=j.collect(cfg,path,NOW)
   self.assertEqual(path.read_bytes(),before);self.assertEqual({p['id'] for p in items},{'original-1','original-2'});self.assertEqual({p['id']:p['journal_relevance']['status'] for p in items},{'original-1':'relevant','original-2':'pending'})
   self.assertEqual({k:health[0]['counters'][k] for k in ['relevant','pending','excluded','abstracts_recovered']},{'relevant':1,'pending':1,'excluded':1,'abstracts_recovered':3});self.assertEqual(health[0]['count'],2);self.assertEqual(updated['metadata_budget']['requests'],10)
   for row in updated['journals'][J['id']]['records'].values():self.assertEqual(row['first_seen'],'2026-10-20T00:00:00+00:00');self.assertTrue(row['item_id'].startswith('original-'))
 def test_disabled_and_omitted_metadata_add_no_recovery_http(self):
  for enabled in (False,None):
   with self.subTest(enabled=enabled),tempfile.TemporaryDirectory() as tmp:
    cfg=self.configs(tmp,enabled);path=Path(tmp)/'state.json';path.write_text(json.dumps(state()))
    with patch.object(j,'_journal',side_effect=adapter),patch.object(m,'enrich_candidates',side_effect=AssertionError('Recovery forbidden')) as recovery,patch.object(m.requests,'Session',side_effect=AssertionError('HTTP forbidden')):
     _,_,_,updated=j.collect(cfg,path,NOW);recovery.assert_not_called();self.assertEqual(updated['metadata_budget'],state()['metadata_budget'])
 def test_later_taxonomy_or_validation_failure_does_not_commit_recovered_state(self):
  for stage in ('taxonomy','validation'):
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TOPICS_MODE':'v2'},clear=True):
    root=Path(tmp);cfg=self.configs(tmp);data=root/'data';data.mkdir();path=data/'journal-state.json';path.write_text(json.dumps(state()));index=data/'index.json';index.write_text(json.dumps({'schema_version':2,'generated_at':NOW.isoformat(),'items':[],'sources':[],'taxonomy':{'topics':[],'identity_version':'hmac-v1','status':'ok'}}));before=(index.read_bytes(),path.read_bytes());source=root/'sources.json';source.write_text(json.dumps({'sources':[],'journals_config':cfg.name,'lookback_days':30,'max_items_per_source':12,'summary_budget':2}))
    def recovery(doi,title,budget):budget.reserve();return POSITIVE,None
    taxonomy={'topics':[],'identity_version':'hmac-v1','status':'stale' if stage=='taxonomy' else 'ok'}
    with patch.object(collect,'NOW',NOW),patch.object(j,'_journal',side_effect=adapter),patch.object(m,'_crossref',side_effect=recovery) as request,patch.object(collect.site_topics,'read_taxonomy',return_value=(taxonomy,[])),patch.object(collect.site_topics,'classify',return_value={'status':'ok','classified':0,'unclassified':1}),patch.object(collect,'summarize') as summary,patch.object(m.requests,'Session',side_effect=AssertionError('HTTP forbidden')),contextlib.redirect_stdout(io.StringIO()):
     validation=patch.object(topics_schema,'validate_archive',side_effect=ValueError('Synthetic failure')) if stage=='validation' else contextlib.nullcontext()
     with validation,self.assertRaises(collect.UpdateFailure) as caught:collect.run(argparse.Namespace(config=source,data_dir=data,source=None,paper_export=None,no_summary=False,summary_budget=2))
    self.assertEqual(caught.exception.stage,stage);self.assertEqual(request.call_count,1);summary.assert_not_called();self.assertEqual((index.read_bytes(),path.read_bytes()),before);self.assertFalse((data/'daily').exists())
if __name__=='__main__':unittest.main()
