"""Public immutable deployment pointers; rollback never reruns collection or LLMs."""
import argparse,hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone

ASSETS=('index.html','app.js','style.css','favicon.svg')

def write_manifest(output,code_revision,archive_revision,builder_revision=None,mode='publish'):
    for revision in (code_revision,archive_revision,builder_revision or code_revision):
        if not re.fullmatch(r'[0-9a-f]{40}',revision): raise ValueError('An immutable full Git commit is required')
    if mode not in ('publish','rollback','preview','retention'): raise ValueError('Unknown deployment mode')
    output=Path(output);index=output/'data'/'index.json'
    data=json.loads(index.read_text())
    from topics_schema import validate_archive
    validate_archive(data)
    assets={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in (*ASSETS,'schema-support.json') if (output/name).exists()}
    if any(name not in assets for name in ASSETS): raise ValueError('Missing frontend asset')
    manifest={'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(),'mode':mode,'code_revision':code_revision,'archive_revision':archive_revision,'builder_revision':builder_revision or code_revision,'archive_schema':data['schema_version'],'archive_generated_at':data['generated_at'],'archive_sha256':hashlib.sha256(index.read_bytes()).hexdigest(),'assets':assets,'item_count':len(data['items']),'taxonomy_version':data.get('taxonomy',{}).get('version'),'classification':data.get('taxonomy',{}).get('classification',{}),'source_kind':'public_archive','llm_requests':0}
    temporary=output/'deployment-manifest.json.tmp';temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');temporary.replace(output/'deployment-manifest.json')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--code-revision',required=True);p.add_argument('--archive-revision',required=True);p.add_argument('--builder-revision');p.add_argument('--mode',choices=['publish','rollback','preview','retention'],default='publish');a=p.parse_args();m=write_manifest(a.output,a.code_revision,a.archive_revision,a.builder_revision,a.mode);print('Public deployment manifest written:',m['item_count'],'items')
