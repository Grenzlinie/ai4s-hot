"""Public v2 archive contract. No private fields are permitted in labels."""
from topics_v1 import topic_ancestors

def validate_archive(payload):
    if payload.get('schema_version') not in (1,2): raise ValueError('Unsupported archive schema')
    allowed_root={'schema_version','generated_at','timezone','items','taxonomy','sources','summaries','policy'}
    if set(payload)-allowed_root: raise ValueError('Unexpected archive fields')
    allowed_taxonomy={'topics','aliases','identity_version','identity_key_id','version','status','last_success','method','definition_version','classification','error_type'}
    if set(payload.get('taxonomy',{}))-allowed_taxonomy: raise ValueError('Unexpected taxonomy fields')
    classification=payload.get('taxonomy',{}).get('classification',{})
    if set(classification)-{'status','classified','unclassified','algorithm','calibration_status','curation','method'}: raise ValueError('Unexpected classification receipt fields')
    if set(classification.get('curation',{}))-{'status','applied','needs_review'}: raise ValueError('Unexpected curation receipt fields')
    topics=payload.get('taxonomy',{}).get('topics',[])
    known={t['id'] for t in topics}
    if len(known)!=len(topics): raise ValueError('Duplicate public topic identity')
    for t in topics:
        if set(t)-{'id','name','path','parent_id','facet','active','retired','aliases','catalog_path'}: raise ValueError('Private taxonomy field')
        topic_ancestors([t['id']],topics)
    ids=set()
    for item in payload['items']:
        allowed_item={'affiliations','alpha_rank','authors','excerpt','first_seen','group','groups','hf_url','id','pdf_url','published_at','source_ids','source_names','summary','summary_kind','tags','title','topic_ids','topic_leaf_ids','topic_method','topic_version','type','kind','url','zotero_score','doi','arxiv_id','topic_labels','topic_status','topic_scope','content_kind','domain_facets','topic_coverage','topic_cache_token','topic_backend','topic_override'}
        if set(item)-allowed_item: raise ValueError('Unexpected public item fields')
        if item['id'] in ids: raise ValueError('Duplicate public item identity')
        ids.add(item['id'])
        if not set(item.get('topic_ids',[]))<=known or not set(item.get('topic_leaf_ids',[]))<=known: raise ValueError('Unknown topic reference')
        for label in item.get('topic_labels',[]):
            if set(label)-{'id','facet','method','score','confidence','status','public_reason'}: raise ValueError('Unexpected label fields')
            if label['id'] not in known: raise ValueError('Unknown label')
    receipts=[item['topic_override'] for item in payload['items'] if 'topic_override' in item]
    if receipts:
        from topics_curate import validate_overrides
        validate_overrides({'schema_version':1,'overrides':receipts},payload['items'],payload['taxonomy'],allow_retired=True)
    return payload
