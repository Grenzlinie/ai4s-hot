#!/usr/bin/env python3
"""500 real private references / 200 fresh public inputs, cold + warm CPU receipts.

No titles, private reference IDs, embeddings, labels, or per-item errors are output.
Insufficient real references remain a failed gate; they are never duplicated.
"""
import argparse,copy,json,os,pathlib,platform,resource,subprocess,sys,time
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'site'))
from topics_evaluate import digest,exclude_holdout_references

def peak_rss_bytes():
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform=='darwin' else raw*1024)

def stage(dataset,backend,stage_name):
    started=time.monotonic();os.environ['TOPICS_MODE']='v2'
    from site_topics import read_taxonomy
    from topics_corpus import prepare
    from topics_classifier import classify_v2
    taxonomy,refs=read_taxonomy(dataset['taxonomy'],datetime.now(timezone.utc).isoformat())
    network=time.monotonic()-started
    if taxonomy.get('status')!='ok':raise ValueError('Fresh taxonomy required')
    # Public identity order is deterministic; every prediction cache is stripped.
    chosen=sorted(dataset['records'],key=lambda r:r['id'])[:200]
    if len(chosen)<200:raise ValueError('At least 200 distinct public inputs required')
    exclusion_data=copy.deepcopy(dataset['records'])
    chosen_ids={r['id'] for r in chosen}
    for row in exclusion_data:
        if row['id'] in chosen_ids:row['split']='holdout'
    refs,exclusion=exclude_holdout_references(exclusion_data,refs)
    refs=prepare(refs);available=len(refs)
    if available<500:
        return {'stage':stage_name,'status':'insufficient_references','reference_n':available,'required_reference_n':500,'public_item_n':len(chosen),'network_seconds':round(network,4),'total_seconds':round(time.monotonic()-started,4),'peak_rss_bytes':peak_rss_bytes(),'runtime_pass':False,'reference_exclusion':exclusion}
    refs=refs[:500]
    fields=('id','title','excerpt','url','doi','arxiv_id','type','kind')
    items=[{k:copy.deepcopy(row['item'][k]) for k in fields if k in row['item']} for row in chosen]
    classify_start=time.monotonic()
    result=classify_v2(items,taxonomy,refs,force=True,overrides_payload={'schema_version':1,'overrides':[]},backend=backend)
    inference=time.monotonic()-classify_start;total=time.monotonic()-started;rss=peak_rss_bytes()
    actual_backend={item.get('topic_backend') for item in items}
    degraded=result.get('status')=='degraded'
    return {'stage':stage_name,'status':'degraded' if degraded else 'ok','backend_requested':backend,'backend_actual':sorted(x for x in actual_backend if x),'reference_n':len(refs),'available_deduplicated_reference_n':available,'public_item_n':len(items),'force':True,'classified_n':result.get('classified'),'network_seconds':round(network,4),'classification_seconds':round(inference,4),'total_seconds':round(total,4),'peak_rss_bytes':rss,'rss_unit':'bytes','runtime_pass':not degraded and result.get('classified')==200 and total<=(600 if stage_name=='cold' else 300) and rss<=5*1024**3,'reference_exclusion':exclusion,'gold_consumed':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',type=pathlib.Path,default=ROOT/'site/topics/evaluation/annotation-dataset.json');p.add_argument('--output',type=pathlib.Path);p.add_argument('--backend',choices=['lexical','semantic','fusion'],default='lexical');p.add_argument('--model-cache',type=pathlib.Path);p.add_argument('--internal-stage',choices=['cold','warm'],help=argparse.SUPPRESS);a=p.parse_args();data=json.loads(a.dataset.read_text())
    if a.model_cache:os.environ['HF_HOME']=str(a.model_cache.resolve())
    if a.internal_stage:
        try:print(json.dumps(stage(data,a.backend,a.internal_stage)))
        except Exception as error:
            print(json.dumps({'stage':a.internal_stage,'status':'error','error_type':type(error).__name__,'runtime_pass':False}));raise SystemExit(2)
        return
    if not a.output:raise ValueError('--output required')
    preexisting=bool(a.model_cache and a.model_cache.exists() and any(a.model_cache.iterdir()))
    stages=[]
    for name in ('cold','warm'):
        command=[sys.executable,str(pathlib.Path(__file__).resolve()),'--dataset',str(a.dataset.resolve()),'--backend',a.backend,'--internal-stage',name]
        if a.model_cache:command+=['--model-cache',str(a.model_cache.resolve())]
        try:
            child=subprocess.run(command,capture_output=True,text=True,timeout=660 if name=='cold' else 360)
            try:receipt=json.loads(child.stdout)
            except json.JSONDecodeError:receipt={'stage':name,'status':'error','runtime_pass':False,'error_type':'InvalidChildReceipt'}
        except subprocess.TimeoutExpired:
            receipt={'stage':name,'status':'timeout','runtime_pass':False,'error_type':'ClassificationTimeout'}
        stages.append(receipt)
    model_cold_verified=a.backend=='lexical' or (a.model_cache is not None and not preexisting)
    result={'schema_version':1,'dataset_sha256':digest(data),'code_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'runner':{'platform':platform.platform(),'python':platform.python_version(),'cpu_count':os.cpu_count()},'backend':a.backend,'stages':stages,'model_cold_cache_verified':model_cold_verified,'runtime_pass':all(x['runtime_pass'] for x in stages) and model_cold_verified,'quality_pass':False,'quality_note':'Performance receipt only; human labels and quality gates are separate.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);temporary=a.output.with_suffix(a.output.suffix+'.tmp');temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');temporary.replace(a.output)
    print(json.dumps({'runtime_pass':result['runtime_pass'],'quality_pass':False,'stage_statuses':[x['status'] for x in stages]}));raise SystemExit(0 if result['runtime_pass'] else 2)
if __name__=='__main__':main()
