"""Independent bounded enrichment checks. All network/CLI operations are mocked."""
import contextlib,copy,io,json,os,runpy,sys,tempfile,unittest
import yaml
from pathlib import Path
from unittest.mock import Mock,patch
SITE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SITE))
import enrichment as e
import collect
from topics_schema import validate_archive

CONFIG={**e.DEFAULTS,'enabled':True,'bohr_enabled':True,'bohr_daily_calls':2}
def item(i='a',**kw):
 return {'id':i,'title':'Public paper','url':'https://www.nature.com/articles/s41586-026-12345-0','doi':'10.1038/s41586-026-12345-0','group':'science','published_at':'2026-10-13','first_seen':'2026-10-13','type':'paper','excerpt':'Public abstract',**kw}
def graph(doi='10.1038/s41586-026-12345-0'):
 return {'ok':True,'data':{'items':[{'paper':{'doi':doi,'private_reference':'PRIVATE_REF'},'graph':{'nodes':[{'kind':'subproblem','content':'Question'},{'kind':'weak_point','content':'Limit'},{'kind':'conclusion','content':'Result'}]}}]},'billing':'PRIVATE_ACCOUNT'}
def cli_payload(payload):
 def run(*args,**kwargs):
  kwargs['stdout'].write(json.dumps(payload).encode());return Mock(returncode=0)
 return run
def response(chunks=(b'<html>Public</html>',),url='https://arxiv.org/html/2601.12345'):
 r=Mock(status_code=200,headers={'Content-Type':'text/html'},url=url);r.__enter__=Mock(return_value=r);r.__exit__=Mock(return_value=False);r.iter_content.return_value=iter(chunks);return r
class EnrichmentTests(unittest.TestCase):
 def setUp(self):
  self.env=patch.dict(os.environ,{'BOHR_ACCESS_KEY':'SYNTHETIC_PRIVATE_KEY'},clear=True);self.env.start();self.addCleanup(self.env.stop)
 def test_public_priority_has_no_cli_and_existing_summary_skipped(self):
  with patch.object(e,'public_text',return_value={'kind':'public_html','text':'A'*900,'url':'https://www.nature.com/article'}) as public,patch.object(e.subprocess,'run',side_effect=AssertionError('No CLI')):
   data,r=e.enrich([item(),item('old',summary='Keep original')],[],CONFIG,2)
  self.assertEqual(set(data),{'a'});self.assertEqual(public.call_count,1);self.assertEqual(r['bohr_calls'],0)
 def test_arxiv_conversion_and_bounded_text(self):
  with patch.object(e.requests,'get',return_value=response()) as get,patch.object(e.trafilatura,'extract',return_value='A'*40000):
   out=e.public_text('https://arxiv.org/pdf/2601.12345v2.pdf',e.EXTRA_HOSTS,CONFIG)
  self.assertEqual(get.call_args.args[0],'https://arxiv.org/html/2601.12345v2');self.assertEqual(len(out['text']),12000);self.assertEqual(get.call_args.kwargs['timeout'],12);self.assertTrue(get.call_args.kwargs['stream']);self.assertFalse(get.call_args.kwargs['allow_redirects'])
 def test_unsafe_urls_and_ports_rejected(self):
  for url in ['http://arxiv.org/a','https://127.0.0.1/a','https://localhost/a','https://arxiv.org.evil/a','https://user:secret@arxiv.org/a','https://arxiv.org:444/a']:
   with self.subTest(url=url),self.assertRaises(ValueError):e.checked_url(url,e.EXTRA_HOSTS)
 def test_redirect_private_target_never_requested(self):
  r=response();r.status_code=302;r.headers={'Location':'https://127.0.0.1/private'}
  with patch.object(e.requests,'get',return_value=r) as get,self.assertRaises(ValueError):e.public_text('https://arxiv.org/abs/2601.12345',e.EXTRA_HOSTS,CONFIG)
  self.assertEqual(get.call_count,1)
 def test_html_document_size_guard(self):
  with patch.object(e.requests,'get',return_value=response([b'x'*65536]*31)),patch.object(e.trafilatura,'extract') as extract,self.assertRaises(ValueError):e.public_text('https://arxiv.org/abs/2601.12345',e.EXTRA_HOSTS,CONFIG)
  extract.assert_not_called()
 def test_challenge_is_not_evidence(self):
  with patch.object(e.requests,'get',return_value=response()),patch.object(e.trafilatura,'extract',return_value='Access denied '+'x'*900),self.assertRaises(ValueError):e.public_text('https://arxiv.org/html/2601.12345',e.EXTRA_HOSTS,CONFIG)
 def test_doi_derived_or_normalized_and_empty_rejected(self):
  self.assertEqual(e.doi_for(item(doi=' https://doi.org/10.1038/TEST ')),'10.1038/test');self.assertIsNone(e.doi_for(item(doi=' ',url='https://arxiv.org/abs/2601.12345')))
  self.assertEqual(e.doi_for(item(doi=None)),'10.1038/s41586-026-12345-0')
 def test_exact_graph_identity_and_kind_no_account(self):
  with patch.object(e.subprocess,'run',side_effect=cli_payload(graph())) as cli:out=e.graph_text(item()['doi'],CONFIG)
  self.assertEqual(out['text'],'[conclusion] Result\n[weak_point] Limit\n[subproblem] Question');self.assertNotIn('PRIVATE',json.dumps(out));self.assertEqual(cli.call_args.kwargs['timeout'],60)
  with patch.object(e.subprocess,'run',side_effect=cli_payload(graph('10.1038/different'))),self.assertRaises(ValueError):e.graph_text(item()['doi'],CONFIG)
 def test_graph_oversize_rejected_before_json_parse(self):
  def large(*args,**kw):kw['stdout'].write(b'x'*2_000_001);return Mock(returncode=0)
  with patch.object(e.subprocess,'run',side_effect=large),patch.object(e.json,'loads') as parse,self.assertRaises(ValueError):e.graph_text(item()['doi'],CONFIG)
  parse.assert_not_called()
 def test_failure_is_anonymous_and_allowance_limits_failed_calls(self):
  with patch.object(e,'public_text',side_effect=ValueError('PRIVATE_HTML')),patch.object(e.subprocess,'run',return_value=Mock(returncode=1,stdout='PRIVATE_ACCOUNT',stderr='PRIVATE_ACCOUNT')) as cli:
   data,r=e.enrich([item('a'),item('b'),item('c')],[],CONFIG,1)
  self.assertEqual(cli.call_count,1);self.assertEqual(r['bohr_calls'],1);self.assertEqual(r['fallback'],3);self.assertFalse(data);self.assertNotIn('PRIVATE',json.dumps(r))
 def test_allowance_zero_and_no_key_have_zero_cli_calls(self):
  for allowance,has_key in [(0,True),(2,False)]:
   with self.subTest(allowance=allowance),patch.dict(os.environ,{'BOHR_ACCESS_KEY':'x'} if has_key else {},clear=True),patch.object(e,'public_text',side_effect=ValueError()),patch.object(e.subprocess,'run') as cli:
    e.enrich([item()],[],CONFIG,allowance);cli.assert_not_called()
 def test_budget_limits_cap_attempts_and_no_summary_mutation(self):
  rows=[item(str(i)) for i in range(5)];before=copy.deepcopy(rows)
  with patch.object(e,'public_text',side_effect=ValueError()),patch.object(e,'graph_text',side_effect=ValueError()) as graph_call:
   _,r=e.enrich(rows,[],{**CONFIG,'max_items':3},99)
  self.assertEqual(r['attempted'],3);self.assertEqual(graph_call.call_count,2);self.assertEqual(rows,before)
 def test_reservation_same_day_exhaustion_next_day_refresh(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger.json';self.assertEqual(e.reserve(p,CONFIG,'2026-10-13'),2);self.assertEqual(e.reserve(p,CONFIG,'2026-10-13'),0);self.assertEqual(e.reserve(p,CONFIG,'2026-10-14'),2);self.assertEqual(json.loads(p.read_text()),{'date':'2026-10-14','reserved':2})
 def test_invalid_ledger_fails_closed(self):
  for bad in ['not json',json.dumps({'date':'2026-10-13','reserved':True}),json.dumps({'date':'2026-10-13','reserved':-1}),json.dumps({'date':'2026-10-14','reserved':0}),json.dumps({'date':'0000-bad','reserved':100})]:
   with self.subTest(bad=bad),tempfile.TemporaryDirectory() as d:
    p=Path(d)/'ledger.json';p.write_text(bad);self.assertEqual(e.reserve(p,CONFIG,'2026-10-13'),0);self.assertEqual(p.read_text(),bad)
 def test_reservation_disabled_or_no_key_does_not_touch_ledger(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{},clear=True):
   p=Path(d)/'ledger.json';self.assertEqual(e.reserve(p,CONFIG,'2026-10-13'),0);self.assertFalse(p.exists())
 def test_settings_reject_unbounded_or_unknown_config(self):
  for change in [{'max_chars':24001},{'max_items':25},{'bohr_daily_calls':101},{'timeout':31},{'enabled':'yes'},{'private_key':'x'}]:
   with self.subTest(change=change),patch.dict(os.environ,{'CUSTOM_CONFIG':json.dumps({'enrichment':change})}),self.assertRaises(ValueError):e.settings()
 def test_summary_public_inputs_only_and_basis_has_no_text(self):
  row=item(private_reference='PRIVATE_REF');content={'kind':'bohr_knowledge_graph','text':'[weak_point] Public limitation','url':'https://doi.org/'+row['doi'],'sha256':'a'*64}
  reply=Mock();reply.json.return_value={'choices':[{'message':{'content':'Public summary'}}]}
  with patch.dict(os.environ,{'OPENAI_API_KEY':'SYNTHETIC','OPENAI_API_BASE':'https://mock.invalid/v1'}),patch.object(collect,'summary_config',return_value='synthetic'),patch.object(collect,'summary_options',return_value={'max_tokens':1024}),patch.object(collect.requests,'post',return_value=reply) as post:
   result=collect.summarize([row],1,{'a':content})
  self.assertEqual(result['generated'],1);self.assertNotIn('PRIVATE',json.dumps(post.call_args.kwargs['json']));self.assertEqual(set(row['summary_basis']),{'kind','url','sha256','chars'});self.assertNotIn('text',row['summary_basis'])
 def test_existing_summary_not_regenerated(self):
  row=item(summary='Original');before=copy.deepcopy(row)
  with patch.dict(os.environ,{'OPENAI_API_KEY':'x','OPENAI_API_BASE':'https://mock.invalid'}),patch.object(collect,'summary_config',return_value='synthetic'),patch.object(collect.requests,'post') as post:collect.summarize([row],1,{'a':{'text':'new'}})
  post.assert_not_called();self.assertEqual(row,before)
 def test_basis_schema_rejects_raw_evidence_fields(self):
  payload={'schema_version':2,'items':[{'id':'a','summary_basis':{'kind':'public_html','url':'https://example.org','sha256':'a'*64,'chars':800}}],'taxonomy':{'topics':[]}}
  validate_archive(payload);payload['items'][0]['summary_basis']['text']='PRIVATE_TEXT'
  with self.assertRaises(ValueError):validate_archive(payload)
 def test_site_configuration_removed_before_upstream(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'CUSTOM_CONFIG':json.dumps({'enrichment':{'enabled':True},'email':{'smtp':'private'},'llm':{'model':'synthetic'}})}):
   (Path(d)/'config').mkdir();old=os.getcwd()
   try:os.chdir(d);runpy.run_path(str(SITE/'prepare_config.py'));text=(Path(d)/'config/custom.yaml').read_text()
   finally:os.chdir(old)
  self.assertNotIn('enrichment',text);self.assertNotIn('smtp',text);self.assertIn('synthetic',text)
 def test_workflow_reservation_push_precedes_allowance_and_collect(self):
  text=(SITE.parent/'.github/workflows/ai4s-pages.yml').read_text();start=text.index('- name: Reserve daily Bohrium');end=text.index('- uses: actions/setup-node',start);step=text[start:end]
  self.assertLess(step.index('push origin HEAD:site-data'),step.index('echo "allowance='));self.assertNotIn('--force',step);self.assertNotIn('continue-on-error',step);self.assertIn('cancel-in-progress: false',text);self.assertIn("steps.bohr_cli.outcome == 'success' && steps.bohr_budget.outputs.allowance || '0'",text)
 def test_merge_summary_basis_tracks_only_current_summary(self):
  old_basis={'kind':'public_html','url':'https://example.org/old','sha256':'a'*64,'chars':900}
  new_basis={'kind':'bohr_knowledge_graph','url':'https://doi.org/10.1038/new','sha256':'b'*64,'chars':1000}
  for scenario,new_summary,basis in [('no summary',None,None),('new summary without basis','New upstream TLDR',None),('new summary with basis','New grounded summary',new_basis)]:
   with self.subTest(scenario=scenario):
    old=item(summary='Original grounded summary',summary_kind='ai_summary',summary_basis=copy.deepcopy(old_basis),source_ids=['original'],source_names=['Original'],tags=[])
    incoming=item(source_ids=['upstream'],source_names=['Upstream'],tags=[])
    if new_summary:incoming.update(summary=new_summary,summary_kind='upstream_tldr')
    if basis:incoming['summary_basis']=copy.deepcopy(basis)
    state={'a':old};collect.merge(state,[incoming]);current=state['a']
    if new_summary is None:
     self.assertEqual(current['summary'],'Original grounded summary');self.assertEqual(current['summary_basis'],old_basis);self.assertEqual(current['summary_kind'],'ai_summary')
    elif basis is None:
     self.assertEqual(current['summary'],new_summary);self.assertNotIn('summary_basis',current)
    else:
     self.assertEqual(current['summary'],new_summary);self.assertEqual(current['summary_basis'],new_basis)
 def test_cloud_cli_failure_has_zero_allowance_and_version_pinned(self):
  workflow=yaml.safe_load((SITE.parent/'.github/workflows/ai4s-pages.yml').read_text());steps=workflow['jobs']['build']['steps'];byid={step['id']:step for step in steps if 'id' in step}
  node,cli,collector=byid['bohr_node'],byid['bohr_cli'],byid['collect']
  self.assertIs(node['continue-on-error'],True);self.assertIs(cli['continue-on-error'],True)
  self.assertIn("steps.bohr_node.outcome == 'success'",cli['if']);self.assertIn('@dptech-corp/bohr-cli@2.7.11',cli['run'])
  self.assertEqual(collector['env']['BOHR_CALL_ALLOWANCE'],"${{ steps.bohr_cli.outcome == 'success' && steps.bohr_budget.outputs.allowance || '0' }}")
  self.assertEqual(cli['env']['BOHR_ACCESS_KEY'],'${{ secrets.BOHR_ACCESS_KEY }}');self.assertNotIn('BOHR_ACCESS_KEY',cli['run']);self.assertNotIn('print(result',cli['run']);self.assertNotIn('print(payload',cli['run'])
 def test_cloud_auth_verification_is_strict_and_output_anonymous(self):
  workflow=yaml.safe_load((SITE.parent/'.github/workflows/ai4s-pages.yml').read_text());step=next(s for s in workflow['jobs']['build']['steps'] if s.get('id')=='bohr_cli');code=step['run'].split("python - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
  for ok,verified,expected in [(True,True,True),(True,'true',False),(True,1,False),(False,True,False),(True,False,False)]:
   with self.subTest(ok=ok,verified=verified):
    stdout=io.StringIO();reply=Mock(returncode=0,stdout=json.dumps({'ok':ok,'data':{'verified':verified,'account':'PRIVATE_ACCOUNT'}}),stderr='PRIVATE_KEY')
    with patch.object(e.subprocess,'run',return_value=reply) as call,contextlib.redirect_stdout(stdout):
     if expected:exec(compile(code,'workflow-auth','exec'),{})
     else:
      with self.assertRaises(SystemExit):exec(compile(code,'workflow-auth','exec'),{})
    self.assertEqual(stdout.getvalue(),'Bohrium authentication verified: '+str(expected)+'\n');self.assertTrue(call.call_args.kwargs['capture_output']);self.assertEqual(call.call_args.kwargs['timeout'],30);self.assertEqual(call.call_args.args[0],['bohr','auth','status','--verify','-o','json'])
if __name__=='__main__':unittest.main()
