"""Create public shadow output without modifying the production archive."""
import argparse,json,os,sys,time,resource
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'site'))
from site_topics import read_taxonomy
from topics_classifier import classify_v2
from topics_reclassify import atomic_write
from topics_schema import validate_archive


def _run():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    os.environ['TOPICS_MODE']='v2'
    archive=json.loads(a.input.read_text())
    started=time.perf_counter();taxonomy,corpus=read_taxonomy(archive.get('taxonomy',{}),archive['generated_at']);read_seconds=time.perf_counter()-started
    if taxonomy.get('status')!='ok': raise SystemExit('Shadow stopped: fresh valid taxonomy unavailable')
    started=time.perf_counter();result=classify_v2(archive['items'],taxonomy,corpus,force=True);seconds=time.perf_counter()-started
    taxonomy['classification']=result;archive.update(schema_version=2,taxonomy=taxonomy)
    validate_archive(archive);a.output.parent.mkdir(parents=True,exist_ok=True);atomic_write(a.output,archive)
    receipt={'mode':'shadow','production_changed':False,'items':len(archive['items']),'reference_count':len(corpus),'topics':len(taxonomy['topics']),'read_seconds':read_seconds,'classify_seconds':seconds,'rss_platform_raw':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'platform':sys.platform,'backend':result.get('algorithm'),'quality_accepted':False,'reason':'Human-confirmed gold and native acceptance gates are pending'}
    a.receipt.write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))

def main():
    try: _run()
    except Exception as error:
        print(json.dumps({'status':'error','error_type':type(error).__name__,'production_changed':False}),file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__': main()
