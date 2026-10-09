#!/usr/bin/env python3
"""Generate public predictions with private holdout exclusion before any scoring.

No labels or per-item errors are printed. Gold is never passed to a classifier.
"""
import argparse,copy,json,os,pathlib,subprocess,sys,time
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'site'))
from topics_evaluate import adapt_prediction,align_dataset_taxonomy,digest,exclude_holdout_references,leakage_check

def atomic_public(path,payload):
    from tempfile import NamedTemporaryFile
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(mode='w',dir=path.parent,encoding='utf-8',delete=False) as f:
        temporary=pathlib.Path(f.name);json.dump(payload,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    try:temporary.replace(path)
    finally:
        if temporary.exists():temporary.unlink()

def predict(dataset, split, backend, overrides=None):
    start=time.monotonic()
    from site_topics import read_taxonomy
    # Both algorithms receive the same complete identity-bearing private evidence.
    # Production v1 reading remains untouched; only this evaluation reader uses v2.
    previous_mode=os.environ.get('TOPICS_MODE')
    os.environ['TOPICS_MODE']='v2'
    try:
        taxonomy,private_references=read_taxonomy(dataset['taxonomy'],datetime.now(timezone.utc).isoformat())
    finally:
        if previous_mode is None:os.environ.pop('TOPICS_MODE',None)
        else:os.environ['TOPICS_MODE']=previous_mode
    network_seconds=time.monotonic()-start
    if taxonomy.get('status')!='ok':raise ValueError('Fresh valid taxonomy is required')
    safe_references,exclusion=exclude_holdout_references(dataset['records'],private_references)
    if leakage_check(dataset['records'],safe_references)['private_reference_overlap']:
        raise ValueError('Holdout exclusion failed')
    held={r['id'] for r in dataset['records'] if r['split']=='holdout'}
    selected_ids={r['id'] for r in dataset['records'] if r['split']==split}
    original=overrides or {'schema_version':1,'overrides':[]}
    selected_overrides={'schema_version':1,'overrides':[r for r in original['overrides'] if r['item_id'] not in held and r['item_id'] in selected_ids]}
    if leakage_check(dataset['records'],safe_references,[r['item_id'] for r in selected_overrides['overrides']])['override_overlap']:
        raise ValueError('Holdout override exclusion failed')
    # Copy only public model inputs, excluding gold and previous prediction caches.
    fields=('id','title','excerpt','url','doi','arxiv_id','kind','type','source_ids')
    items=[{k:copy.deepcopy(r['item'][k]) for k in fields if k in r['item']} for r in dataset['records'] if r['split']==split]
    classify_start=time.monotonic()
    if backend=='v2':
        from topics_classifier import classify_v2
        result=classify_v2(items,taxonomy,safe_references,force=True,overrides_payload=selected_overrides)
    else:
        from topics_v1 import classify
        result=classify(items,taxonomy,safe_references)
    predictions=[adapt_prediction(item) for item in items]
    receipt={'schema_version':1,'dataset_sha256':digest(dataset),'predictions_sha256':digest(predictions),'split':split,'backend':backend,'taxonomy_reader':'v2_shared_identity','comparison_scope':'algorithm_on_common_stable_taxonomy_and_excluded_references','training_reference_n':len(safe_references),'public_item_n':len(items),'reference_exclusion':exclusion,'holdout_override_excluded_n':sum(r['item_id'] in held for r in original['overrides']),'private_reference_overlap_after':0,'override_overlap_after':0,'taxonomy_version':taxonomy.get('version'),'algorithm':result.get('algorithm',backend),'network_seconds':round(network_seconds,4),'classification_seconds':round(time.monotonic()-classify_start,4),'total_seconds':round(time.monotonic()-start,4),'gold_consumed':False}
    return predictions,receipt,taxonomy

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=pathlib.Path,required=True);p.add_argument('--split',choices=['dev','holdout'],default='dev');p.add_argument('--backend',choices=['v1','v2'],default='v2');p.add_argument('--overrides',type=pathlib.Path,default=ROOT/'site/topics/overrides.json');p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--receipt',type=pathlib.Path,required=True);p.add_argument('--aligned-dataset',type=pathlib.Path);a=p.parse_args()
    data=json.loads(a.dataset.read_text());overrides=json.loads(a.overrides.read_text()) if a.overrides.exists() else None
    predictions,receipt,taxonomy=predict(data,a.split,a.backend,overrides)
    receipt['code_sha']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if a.aligned_dataset:
        aligned=align_dataset_taxonomy(data,taxonomy);receipt['aligned_dataset_sha256']=digest(aligned);atomic_public(a.aligned_dataset,aligned)
    atomic_public(a.output,predictions);atomic_public(a.receipt,receipt)
    print(json.dumps({'public_item_n':receipt['public_item_n'],'split':a.split,'backend':a.backend,'holdout_exclusion_pass':True,'gold_consumed':False,'receipt_written':True}))
if __name__=='__main__':main()
