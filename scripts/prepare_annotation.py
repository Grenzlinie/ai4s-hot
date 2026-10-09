#!/usr/bin/env python3
"""Rebuild frozen public dev data and collect unseen review candidates."""
import argparse, hashlib, json, pathlib, subprocess, sys, time
import feedparser, requests
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'site'))
from topics_evaluate import canonical_id, digest, split_records
ROOT=pathlib.Path(__file__).resolve().parents[1]
COMMIT='d49956853ecf5e74232d330dc4f889dab01b7dba'

def collect():
    items=[]; receipts=[]
    queries=['cat:cond-mat.mtrl-sci','all:"machine learning" AND all:science','all:benchmark AND all:scientific','all:"scientific computing"']
    for query in queries:
        response=requests.get('https://export.arxiv.org/api/query',params={'search_query':query,'start':0,'max_results':25,'sortBy':'submittedDate','sortOrder':'descending'},timeout=60)
        response.raise_for_status(); entries=feedparser.parse(response.text).entries
        if not entries: raise RuntimeError('Empty arXiv source')
        receipts.append({'source':'arxiv','query':query,'url':response.url,'response_sha256':hashlib.sha256(response.content).hexdigest(),'count':len(entries)})
        for e in entries:
            url=e.link
            items.append({'id':hashlib.sha256(url.encode()).hexdigest()[:20],'url':url,'title':' '.join(e.title.split()),'excerpt':' '.join(e.summary.split()),'type':'paper','published_at':e.get('published'),'source_names':['arXiv']})
        time.sleep(3)
    response=requests.get('https://openai.com/news/rss.xml',timeout=60);response.raise_for_status()
    entries=feedparser.parse(response.text).entries[:40]
    receipts.append({'source':'OpenAI News','url':response.url,'response_sha256':hashlib.sha256(response.content).hexdigest(),'count':len(entries)})
    for e in entries:
        url=e.link
        items.append({'id':hashlib.sha256(url.encode()).hexdigest()[:20],'url':url,'title':e.title,'excerpt':e.get('summary',''),'type':'report','published_at':e.get('published'),'source_names':['OpenAI News']})
    return items,receipts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collect',action='store_true');parser.add_argument('--public-candidates',type=pathlib.Path);args=parser.parse_args()
    dest=ROOT/'site/topics/evaluation';dest.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',COMMIT+':data/index.json'],cwd=ROOT);baseline=json.loads(raw)
    (dest/'baseline-input.json').write_bytes(raw)
    candidates=[];receipts=[]
    if args.collect:candidates,receipts=collect()
    elif args.public_candidates:
        imported=json.loads(args.public_candidates.read_text())
        candidates=[r['item'] for r in imported['records'] if r['split']=='holdout'] if isinstance(imported,dict) else imported
        old=dest/'dataset-manifest.json'
        if old.exists():receipts=json.loads(old.read_text()).get('source_receipts',[])
    records=split_records(baseline['items'],candidates)
    dataset={'schema_version':1,'taxonomy':baseline['taxonomy'],'records':records}
    (dest/'annotation-dataset.json').write_text(json.dumps(dataset,ensure_ascii=False,indent=2)+'\n')
    manifest={'schema_version':1,'baseline_commit':COMMIT,'baseline_path':'data/index.json','baseline_input_sha256':hashlib.sha256(raw).hexdigest(),'baseline_generated_at':baseline.get('generated_at'),'actual_baseline_count':len(baseline['items']),'design_baseline_count':88,'baseline_discrepancy':'The authoritative commit contains 106 public items. All are retained as dev; no audited item is holdout.','seed':20261009,'deduplication':'Canonical DOI/arXiv/version/normalized URL and normalized title; audited groups always dev.','label_version':'unconfirmed-candidates-v1','dev_n':sum(r['split']=='dev' for r in records),'holdout_n':sum(r['split']=='holdout' for r in records),'dataset_sha256':digest(dataset),'source_receipts':receipts,'samples':[{'id':r['id'],'canonical_id':r['canonical_id'],'identity_aliases':r.get('identity_aliases',[]),'split':r['split'],'input_sha256':digest(r['item'])} for r in records],'human_confirmed_n':0,'quality_ready':False}
    (dest/'dataset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ['actual_baseline_count','dev_n','holdout_n','dataset_sha256','human_confirmed_n','quality_ready']}))
if __name__=='__main__':main()
