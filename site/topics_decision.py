"""Facet-independent decisions. Similarities are not probabilities."""
import re
from collections import defaultdict
from topics_v1 import topic_ancestors

DEFAULTS={'min_score':.24,'relative_score':.82,'margin':.035,'max_per_facet':2,'min_coverage':.12}


def content_facets(item):
    text=(item.get('title','')+' '+item.get('excerpt','')).lower()
    kind=item.get('type',item.get('kind','unknown'))
    organization=bool(re.search(r'\b(?:banking|barclays|fundrais\w*|funding round|partnership|appoint\w*|acquisition|enterprise deployment)\b|\bbank\b.{0,60}\b(?:claude|deploy)',text))
    release=kind in ('release','model_release') or bool(re.search(r'\bintroducing\b|\blaunch(?:es|ing)?\b|model release',text))
    paper=kind=='paper' or 'arxiv.org' in item.get('url','')
    scope='non_research' if organization or (release and not paper) else ('research' if paper or re.search(r'experiment|scientific|research|benchmark|dataset|material|molecular|algorithm',text) else 'unknown')
    content='web:organization_policy' if organization else ('web:model_release' if release and not paper else ('web:paper' if paper else ('web:technical_report' if scope=='research' else 'web:engineering_update')))
    domains=[]
    for label,pattern in [('materials',r'material|crystal|alloy|polymer|mof|cof|interatomic'),('chemistry',r'chemistry|chemical|molecul|cataly|reaction'),('life_sciences',r'protein|biolog|genom|drug|medical')]:
        if re.search(pattern,text): domains.append('web:'+label)
    return scope,content,domains or ['web:general_ai']


def decide(item,topics,scores,coverage,exact,config):
    by_id={t['id']:t for t in topics if t.get('active',True)}
    children={t.get('parent_id') for t in by_id.values()}
    roots={t:next(a for a in topic_ancestors([t],topics) if not by_id[a].get('parent_id')) for t in by_id}
    scope,kind,domains=content_facets(item)
    text=item.get('title','')+' '+item.get('excerpt','')
    automatic_method='local_'+config.get('backend','lexical')+'_v2'
    if exact:
        chosen=[t for t in exact if t in by_id]; status='classified'; method='zotero_exact'
    elif scope=='non_research': chosen=[];status='classified';method='scope_rule'
    elif len(item.get('excerpt','').strip())<40:
        chosen=[];status='insufficient_evidence';method=automatic_method
    else:
        grouped=defaultdict(list)
        if coverage<config['min_coverage'] and config.get('backend','lexical')=='lexical':
            return {'topic_labels':[], 'topic_leaf_ids':[], 'topic_ids':[], 'topic_status':'taxonomy_gap','topic_scope':scope,'content_kind':kind,'domain_facets':domains,'topic_method':automatic_method,'topic_coverage':round(coverage,4)}
        for t,record in scores.items():
            if t not in by_id: continue
            rules=record.get('rules',[])
            if 'require_acquisition_evidence' in rules and not record['definition_hit']: continue
            if 'require_scientific_task' in rules and not (record['definition_hit'] and re.search(r'scien|research|laborator|experiment|科研|实验',text,re.I)): continue
            grouped[roots[t]].append((record['score'],t))
        chosen=[]
        for root,candidates in sorted(grouped.items()):
            facet_path=by_id[root].get('catalog_path',by_id[root]['path'])
            facet_config={**config,**config.get('facet_thresholds',{}).get(facet_path,{})}
            candidates.sort(key=lambda x:(-x[0],x[1]))
            leaves=[(s,t) for s,t in candidates if t not in children or scores[t]['definition_hit']]
            best=leaves[0][0] if leaves else 0
            selected=[t for s,t in leaves if s>=max(facet_config['min_score'],best*facet_config['relative_score'])][:facet_config['max_per_facet']]
            if len(selected)>1 and not any(scores[t]['definition_hit'] for t in selected):
                first,second=leaves[:2]
                if first[0]-second[0]<facet_config['margin']:
                    common=set(topic_ancestors([first[1]],topics))&set(topic_ancestors([second[1]],topics))
                    selected=[max(common,key=lambda t:len(topic_ancestors([t],topics)))] if common else []
            if not selected and candidates and candidates[0][0]>=facet_config['min_score']:
                selected=[candidates[0][1]]
            chosen.extend(selected)
        status=('broad_only' if chosen and all(t in children for t in chosen) else 'classified') if chosen else ('taxonomy_gap' if coverage<config['min_coverage'] else 'low_confidence')
        method=automatic_method
    chosen=sorted(t for t in set(chosen) if not any(t in topic_ancestors([other],topics) for other in chosen if other!=t))
    labels=[]
    for t in chosen:
        score=1.0 if exact else round(scores.get(t,{}).get('score',0),4)
        public_terms=scores.get(t,{}).get('public_terms',[])
        reason=(f'公开标题或摘要包含定义关键词：{"、".join(public_terms)}。' if public_terms else f'公开标题或摘要与“{by_id[t]["name"]}”定义存在相似度证据，需复核。')
        if not exact and scores.get(t,{}).get('cold_start'): reason='仅定义匹配，暂无参考样本；'+reason
        labels.append({'id':t,'facet':roots[t],'method':method,'score':score,'confidence':'exact' if exact else ('low' if scores.get(t,{}).get('cold_start') else ('medium' if score>=.42 else 'low')),'status':('broad_only' if t in children and not exact else status),'public_reason':reason if not exact else '标准文献身份或无冲突标题与本地参考一致。'})
    return {'topic_labels':labels,'topic_leaf_ids':chosen,'topic_ids':topic_ancestors(chosen,topics),'topic_status':status,'topic_scope':scope,'content_kind':kind,'domain_facets':domains,'topic_method':method,'topic_coverage':round(coverage,4)}
