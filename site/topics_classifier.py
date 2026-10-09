"""Versioned local classification with opaque cache receipts."""
import copy,hashlib,hmac,json,os
from pathlib import Path
import yaml
from topics_catalog import load_catalog
from topics_thresholds import validate_thresholds
from topics_corpus import prepare,exact_match
from topics_candidates import LexicalCandidates
from topics_decision import decide,DEFAULTS
from topics_identity import load_private_config
from topics_curate import apply_overrides
from topics_semantic import MODEL,REVISION

ALGORITHM='faceted-local-v2.4'
ROOT=Path(__file__).parent/'topics'

class ClassificationUpdateError(RuntimeError):
    """Safe public attempt failure; prior classification remains authoritative."""
    def __init__(self, failed_item_id=None):
        super().__init__('Local classification failed; previous snapshot retained')
        self.failed_item_id=failed_item_id


def classify_v2(items,taxonomy,corpus,force=False, overrides_payload=None, backend=None):
    working_items=copy.deepcopy(items);working_taxonomy=copy.deepcopy(taxonomy)
    result=_classify_v2(working_items,working_taxonomy,corpus,force,overrides_payload,backend)
    # Commit only after the complete batch and curation succeeded.
    for original,updated in zip(items,working_items): original.clear();original.update(updated)
    taxonomy.clear();taxonomy.update(working_taxonomy)
    return result


def _classify_v2(items,taxonomy,corpus,force=False, overrides_payload=None, backend=None):
    config=load_private_config()
    catalog=load_catalog(ROOT/'catalog.yaml')
    taxonomy['definition_version']=catalog['version']
    thresholds=yaml.safe_load((ROOT/'thresholds.yaml').read_text())
    options=validate_thresholds(thresholds,catalog)
    if backend is not None:
        if backend not in ("lexical","semantic","fusion"): raise ValueError("Unknown local backend")
        options["backend"]=backend
        thresholds={**thresholds,"backend":backend}
    corpus=prepare(corpus)
    topics=[t for t in taxonomy.get('topics',[]) if t.get('active',True)]
    candidates=LexicalCandidates(corpus,topics,catalog)
    semantic=None;degraded=False
    if options.get('backend') in ('semantic','fusion'):
        try:
            from topics_semantic import SemanticCandidates
            semantic=SemanticCandidates(corpus,topics,catalog)
        except (ImportError,OSError,RuntimeError): degraded=True
    overrides_path=ROOT/'overrides.json'
    overrides=json.loads(overrides_path.read_text()) if overrides_path.exists() else {'schema_version':1,'overrides':[]}
    if overrides_payload is not None: overrides=overrides_payload
    common={'algorithm':ALGORITHM,'normalization':'tokens-v1.1-identities-v2','taxonomy':taxonomy.get('version'), 'catalog':catalog,'thresholds':thresholds,'effective_options':options,'model':[MODEL,REVISION], 'corpus':corpus,'overrides':overrides,'degraded':degraded}
    secret=config['id_salt'].encode()
    common_digest=hmac.new(secret,json.dumps(common,sort_keys=True,ensure_ascii=False).encode(),hashlib.sha256).digest()
    retired={t['id'] for t in taxonomy.get('topics',[]) if not t.get('active',True) or t.get('retired')}
    for item in items:
        history={l['id']:l for l in item.get('topic_history',[]) if l['id'] in retired}
        history.update({l['id']:l for l in item.get('topic_labels',[]) if l['id'] in retired})
        if history: item['topic_history']=[history[k] for k in sorted(history)]
    changed=0
    for item in items:
        public={k:item.get(k,'') for k in ('title','excerpt','url','doi','arxiv_id','kind','type')}
        token=hmac.new(common_digest,json.dumps(public,sort_keys=True).encode(),hashlib.sha256).hexdigest()
        if not force and item.get('topic_cache_token')==token: continue
        try:
            text=item.get('title','')+' '+item.get('excerpt','')
            scores,coverage=candidates.score(text)
            if semantic:
                semantic_scores=semantic.score(text)
                for t,row in scores.items():
                    value=min(1,max(0,(semantic_scores.get(t,0)-.65)/.35))
                    row['score']=value if options['backend']=='semantic' else .6*row['score']+.4*value
            decision_options={**options,'backend':options['backend'] if semantic is not None else 'lexical'}
            result=decide(item,topics,scores,coverage,exact_match(item,corpus),decision_options)
            if not corpus and not any(r.get('definition_hit') for r in scores.values()) and result['topic_scope']!='non_research':
                result.update(topic_status='pending',topic_labels=[],topic_leaf_ids=[],topic_ids=[])
            item.update(result,topic_cache_token=token,topic_version=ALGORITHM,topic_backend='degraded_lexical' if degraded else options['backend'])
        except Exception:
            raise ClassificationUpdateError(item.get('id')) from None
        changed+=1
    curation=apply_overrides(items,taxonomy,overrides)
    return {'status':'degraded' if degraded else 'ok','classified':changed,'unclassified':sum(not p.get('topic_ids') for p in items),'algorithm':ALGORITHM,'calibration_status':thresholds['calibration_status'],'quality_status':'unmeasured','curation':curation}
