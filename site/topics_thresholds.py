"""Public, versioned per-facet decision configuration."""
import math
from topics_decision import DEFAULTS

NUMERIC={'min_score','relative_score','margin','min_coverage'}
FACET_FIELDS={'min_score','relative_score','margin','max_per_facet'}


def _validate_values(values):
    for key in NUMERIC & set(values):
        number=values[key]
        if isinstance(number,bool) or not isinstance(number,(int,float)) or not math.isfinite(number) or not 0<=number<=1:
            raise ValueError('Threshold must be a finite number between zero and one')
    if 'max_per_facet' in values:
        value=values['max_per_facet']
        if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=2:
            raise ValueError('Automatic facet quota must be one or two')


def validate_thresholds(value,catalog):
    allowed=NUMERIC|{'max_per_facet','version','backend','calibration_status','facet_thresholds'}
    if not isinstance(value,dict) or set(value)-allowed: raise ValueError('Unexpected public threshold fields')
    if value.get('backend','lexical') not in ('lexical','semantic','fusion'): raise ValueError('Unknown local candidate backend')
    if not isinstance(value.get('calibration_status'),str) or not value['calibration_status']: raise ValueError('Calibration status required')
    if 'version' in value and (not isinstance(value['version'],str) or not value['version']): raise ValueError('Threshold version must be nonempty')
    _validate_values(value)
    facets=value.get('facet_thresholds',{})
    names={row['facet'] for row in catalog['topics']}
    if not isinstance(facets,dict) or set(facets)-names: raise ValueError('Unknown configured research facet')
    for config in facets.values():
        if not isinstance(config,dict) or set(config)-FACET_FIELDS: raise ValueError('Unexpected facet threshold fields')
        _validate_values(config)
    return {**DEFAULTS,'backend':'lexical',**value}
