#!/usr/bin/env python3
"""Score frozen public labels; aggregate reports never include holdout errors."""
import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'site'))
from topics_evaluate import adapt_prediction,digest,evaluate,leakage_check,verify_external_receipts

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=pathlib.Path,required=True);p.add_argument('--predictions',type=pathlib.Path,required=True);p.add_argument('--baseline-predictions',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--split',choices=['dev','holdout'],default='holdout');p.add_argument('--evidence',type=pathlib.Path);a=p.parse_args()
    data=json.loads(a.dataset.read_text());pred=json.loads(a.predictions.read_text());base=json.loads(a.baseline_predictions.read_text())
    pred=[adapt_prediction(x) for x in pred];base=[adapt_prediction(x) for x in base]
    baseline=evaluate(data['records'],base,data['taxonomy'],a.split,bootstrap=1000)
    report=evaluate(data['records'],pred,data['taxonomy'],a.split,baseline['metrics']['fine']['f1'],bootstrap=1000)
    leaks=leakage_check(data['records']);report['leakage']=leaks;report['gates']['split_group_exclusion']=not any(leaks.values())
    evidence=json.loads(a.evidence.read_text()) if a.evidence else {}
    report['gates'].update(verify_external_receipts(evidence,data,pred))
    roots=report['metrics']['root_facets'];base_roots=baseline['metrics']['root_facets']
    report['gates']['root_nonregression']=all(v['f1'] is not None and base_roots[k]['f1'] is not None and v['f1']>=base_roots[k]['f1']-.05 for k,v in roots.items() if v['support']>=10)
    report['quality_pass']=all(report['gates'].values());report['baseline_metrics']=baseline['metrics'];report['dataset_sha256']=digest(data);report['predictions_sha256']=digest(pred);report['baseline_predictions_sha256']=digest(base);report['split']=a.split
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'n':report['metrics']['n'],'quality_pass':report['quality_pass'],'failed_gates':[k for k,v in report['gates'].items() if not v]}))
    raise SystemExit(0 if report['quality_pass'] else 2)
if __name__=='__main__':main()
