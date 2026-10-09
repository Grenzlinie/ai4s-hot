"""Inject a failed update through the real collector; no external calls or summaries."""
import argparse,json,pathlib,sys,tempfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'site'))
import collect
from update_status import failure_receipt

def run(stage,data_dir,report):
    index=pathlib.Path(data_dir)/'index.json';before=index.read_bytes();previous=json.loads(before)
    taxonomy={**previous['taxonomy'],'status':'stale' if stage=='taxonomy' else 'ok'}
    with tempfile.TemporaryDirectory() as tmp:
        config=pathlib.Path(tmp)/'sources.json'
        config.write_text(json.dumps({'lookback_days':30,'max_items_per_source':1,'summary_budget':0,'sources':[{'id':'probe','name':'Failure injection','kind':'probe'}]}))
        args=argparse.Namespace(config=config,data_dir=data_dir,paper_export=None,source=None,no_summary=False,summary_budget=0)
        with patch.dict(collect.COLLECTORS,{'probe':lambda *args:[]}),patch('site_topics.read_taxonomy',return_value=(taxonomy,[])),patch('topics_candidates.LexicalCandidates.score',side_effect=RuntimeError('PRIVATE_PROBE_SENTINEL')),patch.object(collect,'summarize',side_effect=AssertionError('Summary must not run during failed classification')),patch.object(collect.requests,'get',side_effect=AssertionError('Network forbidden')):
            try: collect.run(args)
            except collect.UpdateFailure as error:
                if error.stage!=stage or index.read_bytes()!=before: raise AssertionError('Failure did not preserve the archive')
                collect.write_json(report,failure_receipt(stage,collect.NOW.isoformat(),getattr(error,'failed_item_id',None)))
                print('Injected '+stage+' failure: archive unchanged; no summary requests')
                return 2
    raise AssertionError('Failure injection unexpectedly succeeded')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['taxonomy','classification'],required=True);p.add_argument('--data-dir',required=True);p.add_argument('--report',required=True);a=p.parse_args();raise SystemExit(run(a.stage,a.data_dir,a.report))
