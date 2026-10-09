"""Public attempt status, separate from the last valid classification snapshot."""
import argparse,json,re
from datetime import datetime,timezone
from pathlib import Path

STAGES={'taxonomy','classification','validation','build'}
ALLOWED={'status','stage','last_attempt','last_success','error_type','failed_item_id','run_url','retryable'}

def validate_status(value):
    if not isinstance(value,dict) or set(value)-ALLOWED or not {'status','stage','last_attempt','retryable'}<=set(value): raise ValueError('Invalid update status fields')
    if value.get('status') not in ('ok','error') or value.get('stage') not in STAGES: raise ValueError('Invalid update status')
    if not isinstance(value.get('last_attempt'),str): raise ValueError('Update attempt timestamp required')
    for key in ('last_attempt','last_success'):
        if value.get(key) is not None:
            try: stamp=datetime.fromisoformat(value[key].replace('Z','+00:00'))
            except (TypeError,ValueError,AttributeError): raise ValueError('Invalid update timestamp') from None
            if stamp.tzinfo is None: raise ValueError('Timestamp timezone required')
    if value.get('error_type') not in (None,'UpdateFailure'): raise ValueError('Invalid public error type')
    if 'retryable' in value and not isinstance(value['retryable'],bool): raise ValueError('Invalid retry status')
    if value.get('failed_item_id') is not None and (not isinstance(value['failed_item_id'],str) or len(value['failed_item_id'])>200): raise ValueError('Invalid public item identity')
    if value.get('run_url') and not re.fullmatch(r'https://github.com/Grenzlinie/ai4s-hot/actions/runs/[0-9]+',value['run_url']): raise ValueError('Invalid public run URL')
    return value

def failure_receipt(stage,attempt,failed_item_id=None):
    result={'status':'error','stage':stage,'last_attempt':attempt,'last_success':None,'error_type':'UpdateFailure','retryable':True}
    if failed_item_id: result['failed_item_id']=failed_item_id
    return validate_status(result)

def write_status(output,status='ok',stage='classification',failure_report=None,run_url=None):
    output=Path(output);archive=json.loads((output/'data/index.json').read_text())
    from topics_schema import validate_archive
    validate_archive(archive)
    receipt=failure_receipt(stage,datetime.now(timezone.utc).isoformat()) if status=='error' else {'status':'ok','stage':stage,'last_attempt':datetime.now(timezone.utc).isoformat(),'retryable':False}
    if failure_report and Path(failure_report).exists(): receipt=validate_status(json.loads(Path(failure_report).read_text()))
    receipt['last_success']=archive['generated_at']
    if receipt.get('failed_item_id') not in {i['id'] for i in archive['items']}: receipt.pop('failed_item_id',None)
    if run_url: receipt['run_url']=run_url
    validate_status(receipt)
    temporary=output/'update-status.json.tmp';temporary.write_text(json.dumps(receipt,indent=2)+'\n');temporary.replace(output/'update-status.json')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--status',choices=['ok','error'],default='ok');p.add_argument('--stage',choices=sorted(STAGES),default='classification');p.add_argument('--failure-report');p.add_argument('--run-url');a=p.parse_args()
    try: write_status(a.output,a.status,a.stage,a.failure_report,a.run_url)
    except Exception:
        print('Public update status validation failed')
        raise SystemExit(2) from None
