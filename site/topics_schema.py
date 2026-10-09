"""Public v2 archive contract. No private fields are permitted in labels."""
from topics_v1 import topic_ancestors
import math

def validate_archive(payload):
    if payload.get('schema_version') not in (1,2): raise ValueError('Unsupported archive schema')
    allowed_root={'schema_version','generated_at','timezone','items','taxonomy','sources','summaries','policy'}
    if set(payload)-allowed_root: raise ValueError('Unexpected archive fields')
    allowed_taxonomy={'topics','aliases','identity_version','identity_key_id','version','status','last_success','method','definition_version','classification','error_type'}
    if set(payload.get('taxonomy',{}))-allowed_taxonomy: raise ValueError('Unexpected taxonomy fields')
    classification=payload.get('taxonomy',{}).get('classification',{})
    if set(classification)-{'status','classified','unclassified','algorithm','calibration_status','quality_status','curation','method'}: raise ValueError('Unexpected classification receipt fields')
    if set(classification.get('curation',{}))-{'status','applied','needs_review'}: raise ValueError('Unexpected curation receipt fields')
    topics=payload.get('taxonomy',{}).get('topics',[])
    known={t['id'] for t in topics}
    if len(known)!=len(topics): raise ValueError('Duplicate public topic identity')
    for t in topics:
        if set(t)-{'id','name','path','parent_id','facet','active','retired','aliases','catalog_path'}: raise ValueError('Private taxonomy field')
        topic_ancestors([t['id']],topics)
    ids=set()
    for item in payload['items']:
        allowed_item={'affiliations','alpha_rank','authors','excerpt','first_seen','group','groups','hf_url','id','pdf_url','published_at','source_ids','source_names','summary','summary_kind','tags','title','topic_ids','topic_leaf_ids','topic_method','topic_version','type','kind','url','zotero_score','doi','arxiv_id','topic_labels','topic_status','topic_scope','content_kind','domain_facets','topic_coverage','topic_cache_token','topic_backend','topic_override','topic_history'}
        if set(item)-allowed_item: raise ValueError('Unexpected public item fields')
        if item['id'] in ids: raise ValueError('Duplicate public item identity')
        ids.add(item['id'])
        if not set(item.get('topic_ids',[]))<=known or not set(item.get('topic_leaf_ids',[]))<=known: raise ValueError('Unknown topic reference')
        explicit=item.get('topic_leaf_ids',[])
        ancestors=item.get('topic_ids',[])
        if not isinstance(explicit,list) or not isinstance(ancestors,list) or len(set(explicit))!=len(explicit) or len(set(ancestors))!=len(ancestors): raise ValueError('Invalid public label lists')
        if set(ancestors)!=set(topic_ancestors(explicit,topics)): raise ValueError('Topic closure disagrees with explicit labels')
        labels=item.get('topic_labels',[])
        if not isinstance(labels,list): raise ValueError('Invalid public labels')
        if (labels or payload['schema_version']==2) and (len({l.get('id') for l in labels})!=len(labels) or {l.get('id') for l in labels}!=set(explicit)): raise ValueError('Label records disagree with explicit topics')
        history=item.get('topic_history',[])
        retired={t['id'] for t in topics if not t.get('active',True) or t.get('retired')}
        if not isinstance(history,list) or any(not isinstance(l,dict) or l.get('id') not in retired for l in history) or len({l['id'] for l in history})!=len(history): raise ValueError('Invalid retired label history')
        for label in labels+history:
            if set(label)-{'id','facet','method','score','confidence','status','public_reason'}: raise ValueError('Unexpected label fields')
            if label['id'] not in known: raise ValueError('Unknown label')
            root=next(t for t in topics if t['id'] in topic_ancestors([label['id']],topics) and not t.get('parent_id'))
            if label.get('facet')!=root['id']: raise ValueError('Incorrect research facet identity')
            score=label.get('score')
            if score is not None and (isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=1): raise ValueError('Invalid public similarity score')
            if label.get('method') not in {'manual','zotero_exact','local_lexical_v2','local_semantic_v2','local_fusion_v2'}: raise ValueError('Unknown public labeling method')
            if label.get('confidence') not in {'exact','low','medium','high'}: raise ValueError('Unknown confidence band')
            if label.get('status') not in {'classified','broad_only','low_confidence','insufficient_evidence','taxonomy_gap','pending','error'}: raise ValueError('Unknown classification status')
            if not isinstance(label.get('public_reason'),str): raise ValueError('Public classification reason required')
    receipts=[item['topic_override'] for item in payload['items'] if 'topic_override' in item]
    if receipts:
        from topics_curate import validate_overrides
        validate_overrides({'schema_version':1,'overrides':receipts},payload['items'],payload['taxonomy'],allow_retired=True)
    return payload
