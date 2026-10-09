"""Strict public definition catalog; no private reference fields are accepted."""
import argparse
from pathlib import Path
import yaml

RULES={'require_acquisition_evidence','require_scientific_task'}
FIELDS={'path','definition','synonyms','include','exclude','definition_status','facet','rules'}

def validate_catalog(value):
    if not isinstance(value,dict) or set(value)!={'version','topics','web_facets'}:
        raise ValueError('Invalid public catalog document')
    if not isinstance(value['version'],str) or not value['version'].strip():
        raise ValueError('Public definition version required')
    if not isinstance(value['topics'],list) or not value['topics']:
        raise ValueError('Public definitions required')
    seen=set()
    for row in value['topics']:
        if not isinstance(row,dict) or set(row)-FIELDS or not (FIELDS-{'rules'}).issubset(row):
            raise ValueError('Invalid public definition fields')
        for field in ('path','definition','facet'):
            if not isinstance(row[field],str) or not row[field].strip(): raise ValueError('Empty public definition')
        if row['path'] in seen: raise ValueError('Duplicate public definition path')
        seen.add(row['path'])
        if row['definition_status'] not in ('authored','pending'): raise ValueError('Invalid definition status')
        for field in ('synonyms','include','exclude','rules'):
            values=row.get(field,[])
            if not isinstance(values,list) or any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values): raise ValueError('Invalid definition terms')
        if set(row.get('rules',[]))-RULES: raise ValueError('Unknown public decision rule')
    facets=value['web_facets']
    if not isinstance(facets,dict) or set(facets)!={'content_kind','domain'}: raise ValueError('Invalid website facet schema')
    for values in facets.values():
        if not isinstance(values,list) or not values or any(not isinstance(v,str) or not v.startswith('web:') for v in values) or len(set(values))!=len(values): raise ValueError('Invalid website facet identities')
    return value


def load_catalog(path=None):
    return validate_catalog(yaml.safe_load(Path(path or Path(__file__).parent/'topics'/'catalog.yaml').read_text()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path);a=p.parse_args();data=load_catalog(a.catalog);print('Public catalog valid:',len(data['topics']),'definitions')
