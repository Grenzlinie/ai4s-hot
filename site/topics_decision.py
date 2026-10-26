"""Facet-independent decisions. Similarities are not probabilities."""
import re
from collections import defaultdict
from topics_v1 import topic_ancestors
from topics_candidates import phrase_hit

DEFAULTS={'min_score':.24,'relative_score':.82,'margin':.035,'max_per_facet':2,'min_coverage':.12}


def content_facets(item):
    text=(item.get('title','')+' '+item.get('excerpt','')).lower()
    kind=item.get('type',item.get('kind','unknown'))
    # Acquisition functions/data collection and appointment scheduling are
    # scientific activities. Organization evidence requires a business/role context.
    business=r'company|companies|startup|firm|corporate|merger|shares|deal|openai|anthropic|google|microsoft|nvidia|meta'
    acquisition=r'acquisition|acquir(?:e|es|ed|ing)'
    business_text=re.sub(r'\b(?:data|signal|information|knowledge|image|feature)[ -]+acquisition\b|\bacquisition[ -]+functions?\b','',text)
    organization=bool(re.search(r'\b(?:banking|barclays|fundrais\w*|funding round|partnership|enterprise deployment)\b|\bbank\b.{0,60}\b(?:claude|deploy)',text)
        or re.search(r'\b(?:'+business+r')\b.{0,80}\b(?:'+acquisition+r')\b',business_text)
        or re.search(r'\b(?:'+acquisition+r')\b.{0,80}\b(?:company|companies|startup|firm|corporate|merger|shares|deal)\b',business_text)
        or re.search(r'\bannounc(?:e|es|ed|ing)\s+(?:the\s+)?acquisition\b',text)
        or re.search(r'\bappoint(?:s|ed|ing|ment)?\b.{0,80}\b(?:ceo|cto|cfo|chief|president|director|chair|professor|head of)\b',text)
        or re.search(r'\b(?:ceo|cto|cfo|chief|president|director|chair)\b.{0,60}\bappointment\b',text))
    release=kind in ('release','model_release') or bool(re.search(r'\bintroducing\b|\blaunch(?:es|ing)?\b|model release',text))
    paper=kind=='paper' or 'arxiv.org' in item.get('url','')
    scope='non_research' if organization or (release and not paper) else ('research' if paper or re.search(r'experiment|scientific|research|benchmark|dataset|material|molecular|algorithm',text) else 'unknown')
    content='web:organization_policy' if organization else ('web:model_release' if release and not paper else ('web:paper' if paper else ('web:technical_report' if scope=='research' else 'web:engineering_update')))
    domains=[]
    for label,pattern in [('materials',r'material|crystal|alloy|polymer|mof|cof|interatomic'),('chemistry',r'chemistry|chemical|molecul|cataly|reaction'),('life_sciences',r'protein|biolog|genom|drug|medical')]:
        if re.search(pattern,text): domains.append('web:'+label)
    return scope,content,domains or ['web:general_ai']


def title_facet_context(title, facet_path):
    """Generic words are insufficient evidence outside their scientific facet."""
    if facet_path.startswith('02 AI方法'):
        return bool(re.search(r'\b(?:machine[ -]learning|deep[ -]learning|neural[ -](?:networks?|potentials?)|graph learning|artificial intelligence|ai[ -](?:driven|guided|assisted|based)|model training|large language models?|language models?|llms?|gnns?|mlips?|convolutional neural|reinforcement learning|active learning|bayesian optimi[sz]ation|foundation models?|generative models?|generative adversarial|variational autoencoder|autoencoders?|vaes?|gans?|flow matching|normalizing flow|autoregressive|denoising diffusion|diffusion models?|vision transformers?)\b|机器学习|深度学习|神经网络|人工智能|贝叶斯优化',title,re.I))
    if facet_path.startswith('03 数据集与评测'):
        return bool(re.search(r'\b(?:datasets?|databases?|benchmarks?|corpus|data (?:collection|curation|generation|resources?)|evaluation (?:metrics?|methodology|suites?)|model evaluation|model assessment|scoring|grader|verifier)\b|\breproducib\w*\b.{0,50}\b(?:data|code|software|results?)\b|\b(?:data|code|software)\b.{0,50}\breproducib\w*\b|数据集|基准测试|评测指标|代码复现',title,re.I))
    if facet_path.startswith('04 科研软件与计算工作流'):
        return bool(re.search(r'\b(?:software|code|computational|computation|computing|simulation|laborator\w*|workflow|numerical|dft|density functional|molecular dynamics|first[ -]principles|ab initio|robotic\w*|calculations?)\b|软件|代码|计算|实验室|工作流|模拟',title,re.I))
    return True


def decide(item,topics,scores,coverage,exact,config):
    by_id={t['id']:t for t in topics if t.get('active',True)}
    children={t.get('parent_id') for t in by_id.values()}
    roots={t:next(a for a in topic_ancestors([t],topics) if not by_id[a].get('parent_id')) for t in by_id}
    scope,kind,domains=content_facets(item)
    text=item.get('title','')+' '+item.get('excerpt','')
    automatic_method='local_'+config.get('backend','lexical')+'_v2'
    title_hits={}; title_roots=set()
    if exact:
        chosen=[t for t in exact if t in by_id]; status='classified'; method='zotero_exact'
    elif scope=='non_research': chosen=[];status='classified';method='scope_rule'
    elif len(item.get('excerpt','').strip())<40:
        # Title-only classification never uses similarity or corpus neighbours.
        # Every leaf needs an explicit public include phrase present in the title.
        title=item.get('title','')
        for t,record in scores.items():
            if t not in by_id: continue
            facet_path=by_id[roots[t]].get('catalog_path',by_id[roots[t]]['path'])
            if not title_facet_context(title,facet_path): continue
            topic_path=by_id[t].get('catalog_path',by_id[t]['path'])
            if topic_path.startswith('02 AI方法 / 生成模型') and not re.search(r'\b(?:generative|diffusion model|denoising diffusion|flow matching|normalizing flow|autoencoder|autoregressive|vae|gan)\b',title,re.I): continue
            if topic_path.endswith('污染、泄漏、稳健性与复现') and not re.search(r'\b(?:data contamination|data leakage|benchmarks?|model (?:assessment|evaluation|robustness)|adversarial)\b|\breproducib\w*\b.{0,50}\b(?:data|code|software)\b|\b(?:data|code|software)\b.{0,50}\breproducib\w*\b',title,re.I): continue
            if facet_path.startswith('01 材料研究') and re.search(r'\b(?:ocean|acidification|ecosystems?|biodiversity|clinical|patients?|disease|infection)\b',title,re.I) and not re.search(r'\b(?:materials?|crystals?|alloys?|polymers?|electrodes?|electrolytes?|catalysts?|photovoltaics?|semiconductors?|mofs?|cofs?|synthesis|fabrication)\b',title,re.I): continue
            # 'next-generation materials' is not generative modelling evidence.
            hit_title=re.sub(r'\bnext[ -]generation\b','',title,flags=re.I) if facet_path.startswith('02 AI方法') else title
            hits=[term for term in record.get('public_terms',[]) if phrase_hit(term,hit_title)]
            if not hits: continue
            if 'require_scientific_task' in record.get('rules',[]) and not re.search(r'scien|research|laborator|experiment|科研|实验',title,re.I): continue
            title_hits[t]=hits
        grouped=defaultdict(list)
        for t,hits in title_hits.items(): grouped[roots[t]].append(t)
        chosen=[]
        for root,candidates in sorted(grouped.items()):
            specific=[t for t in candidates if not any(t in topic_ancestors([other],topics) for other in candidates if other!=t)]
            facet_config={**config,**config.get('facet_thresholds',{}).get(by_id[root].get('catalog_path',by_id[root]['path']),{})}
            chosen.extend(sorted(specific,key=lambda t:(-len(title_hits[t]),t))[:facet_config['max_per_facet']])
        if scope=='research' and re.search(r'\b(?:materials?|crystals?|alloys?|polymers?|electrolytes?|electrodes?|catalysts?|solid[ -]state)\b|材料',title,re.I):
            for root in set(roots.values()):
                if by_id[root].get('catalog_path',by_id[root]['path']).startswith('01 材料研究') and root not in {roots[t] for t in chosen}:
                    chosen.append(root);title_roots.add(root)
        status=('broad_only' if all(t in children for t in chosen) else 'classified') if chosen else 'insufficient_evidence'
        method=automatic_method
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
        if t in title_hits or t in title_roots:
            reason=('仅依据公开标题直接命中定义关键词：'+ '、'.join(title_hits[t])+'；未使用摘要，需复核。') if t in title_hits else '仅依据公开标题中的明确材料领域词，保留材料研究根类；未使用摘要，不推断叶类。'
        if not exact and scores.get(t,{}).get('cold_start'): reason='仅定义匹配，暂无参考样本；'+reason
        labels.append({'id':t,'facet':roots[t],'method':method,'score':score,'confidence':'exact' if exact else ('low' if t in title_hits or t in title_roots or scores.get(t,{}).get('cold_start') else ('medium' if score>=.42 else 'low')),'status':('broad_only' if t in children and not exact else status),'public_reason':reason if not exact else '标准文献身份或无冲突标题与本地参考一致。'})
    return {'topic_labels':labels,'topic_leaf_ids':chosen,'topic_ids':topic_ancestors(chosen,topics),'topic_status':status,'topic_scope':scope,'content_kind':kind,'domain_facets':domains,'topic_method':method,'topic_coverage':round(coverage,4)}
