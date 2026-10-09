"""Offline backfill, public diff, and atomic archive replacement (no LLM calls)."""
import argparse,json,os,tempfile
from pathlib import Path
from topics_schema import validate_archive
from site_topics import read_taxonomy
from topics_classifier import classify_v2


def atomic_write(path,payload):
    validate_archive(payload)
    path=Path(path)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False,encoding='utf-8') as f:
        temporary=f.name
        json.dump(payload,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    try: os.replace(temporary,path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def run(args):
    payload=json.loads(Path(args.input).read_text())
    if payload.get('schema_version')==1 and args.item:
        raise ValueError('Complete the v1-to-v2 migration before selecting individual items')
    os.environ['TOPICS_MODE']='v2'
    taxonomy,corpus=read_taxonomy(payload.get('taxonomy',{}),payload['generated_at'])
    if taxonomy.get('status')!='ok': raise ValueError('Cannot backfill without a fresh valid taxonomy')
    aliases=taxonomy.get('aliases',{})
    before={p['id']:p.get('topic_leaf_ids',[]) for p in payload['items']}
    for p in payload['items']:
        p['topic_leaf_ids']=[aliases.get(t,t) for t in p.get('topic_leaf_ids',[])]
        p['topic_ids']=[aliases.get(t,t) for t in p.get('topic_ids',[])]
        for label in p.get('topic_labels',[]):
            label['id']=aliases.get(label['id'],label['id'])
            label['facet']=aliases.get(label['facet'],label['facet'])
    selected=[p for p in payload['items'] if not args.item or p['id'] in args.item]
    overrides_path=Path(__file__).parent/'topics'/'overrides.json'
    overrides=json.loads(overrides_path.read_text()) if overrides_path.exists() else {'schema_version':1,'overrides':[]}
    # Validate the complete maintainer file before narrowing it to the backfill set.
    from topics_curate import validate_overrides
    validate_overrides(overrides,payload['items'],taxonomy,allow_retired=True)
    selected_ids={p['id'] for p in selected}
    scoped={'schema_version':1,'overrides':[r for r in overrides['overrides'] if r['item_id'] in selected_ids]}
    taxonomy['classification']=classify_v2(selected,taxonomy,corpus,args.force,overrides_payload=scoped)
    payload.update(schema_version=2,taxonomy=taxonomy)
    validate_archive(payload)
    diff=[{'item_id':p['id'],'before':before[p['id']],'after':p.get('topic_leaf_ids',[]),'status':p.get('topic_status')} for p in selected if before[p['id']]!=p.get('topic_leaf_ids',[])]
    print(json.dumps({'dry_run':not args.output,'selected':len(selected),'changes':diff},ensure_ascii=False,indent=2))
    if args.output: atomic_write(args.output,payload)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output');parser.add_argument('--force',action='store_true');parser.add_argument('--item',action='append')
    try: run(parser.parse_args())
    except Exception:
        print('Reclassification failed; previous snapshot retained')
        raise SystemExit(2) from None
