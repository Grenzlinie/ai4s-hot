"""Public evaluation contracts. Unconfirmed AI suggestions never become gold."""
from __future__ import annotations
import hashlib, json, random, re
from datetime import datetime
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

SEED = 20261009
SCOPES = {'research', 'non_research', 'unknown'}
KINDS = {'paper', 'technicalreport', 'modelrelease', 'engineeringupdate', 'organizationpolicy'}
DOMAIN_FACETS = {'web:materials','web:chemistry','web:life_sciences','web:general_ai'}
STATUSES = {'classified', 'broad_only', 'low_confidence', 'insufficient_evidence', 'taxonomy_gap', 'pending', 'error'}

def canonical_id(item):
    doi = str(item.get('doi', '')).lower().strip()
    text = ' '.join(str(item.get(k, '')) for k in ('url', 'arxiv_id', 'doi'))
    match = re.search(r'(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?', text)
    if match: return 'arxiv:' + match.group(1)
    match = re.search(r'10\.\d{4,9}/[^\s?#]+', doi or text, re.I)
    if match: return 'doi:' + match.group(0).rstrip('/').lower()
    url = urlsplit(str(item.get('url', '')))
    if not url.netloc: raise ValueError('Public canonical URL required')
    return 'url:' + urlunsplit(('https', url.netloc.lower().removeprefix('www.'), url.path.rstrip('/'), '', ''))

def title_alias(item):
    return re.sub(r'[^\w]', '', str(item.get('title', '')).casefold())

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def ancestors(ids, taxonomy):
    parents = {t['id']: t.get('parent_id') for t in taxonomy['topics']}
    result = set()
    for ident in ids:
        seen = set()
        while ident:
            if ident not in parents or ident in seen: raise ValueError('Invalid taxonomy reference')
            seen.add(ident); result.add(ident); ident = parents[ident]
    return result

def specific(ids, taxonomy):
    ids = set(ids)
    redundant = set()
    for ident in ids: redundant |= ancestors([ident], taxonomy) - {ident}
    return ids - redundant

def validate_gold(gold, taxonomy):
    if not isinstance(gold, dict) or gold.get('human_confirmed') is not True:
        raise ValueError('Human confirmation required; AI candidates are not gold')
    allowed = {'human_confirmed','reviewer','reviewed_at','scope','content_kind','domain_facets','acceptable_topic_sets','fine_applicable','status','public_reason'}
    if set(gold) != allowed: raise ValueError('Gold fields missing or unknown')
    if any(not isinstance(gold[k],str) or not gold[k].strip() for k in ('reviewer','reviewed_at','public_reason')): raise ValueError('Reviewer, timestamp and public evidence required')
    try:
        timestamp=datetime.fromisoformat(gold['reviewed_at'].replace('Z','+00:00'))
        if timestamp.tzinfo is None or 'T' not in gold['reviewed_at']:raise ValueError
    except ValueError:raise ValueError('reviewed_at must be an ISO timestamp with timezone') from None
    if gold['scope'] not in SCOPES or gold['content_kind'] not in KINDS or gold['status'] not in STATUSES: raise ValueError('Unknown gold enum')
    if not isinstance(gold['fine_applicable'], bool): raise ValueError('fine_applicable must be boolean')
    if not isinstance(gold['domain_facets'], list) or any(not isinstance(x,str) or x not in DOMAIN_FACETS for x in gold['domain_facets']): raise ValueError('Invalid website facets')
    if len(gold['domain_facets'])!=len(set(gold['domain_facets'])):raise ValueError('Duplicate website facet')
    alternatives = gold['acceptable_topic_sets']
    if not isinstance(alternatives, list) or not alternatives or any(not isinstance(x,list) for x in alternatives): raise ValueError('Complete alternative label sets required')
    for labels in alternatives:
        if any(not isinstance(label,str) for label in labels):raise ValueError('Topic labels must be public IDs')
        if set(labels) != specific(labels, taxonomy) or len(labels) != len(set(labels)): raise ValueError('Gold must use unique most-specific explicit labels')
    if gold['scope'] != 'research' and any(alternatives): raise ValueError('Non-research gold cannot have research labels')
    if not gold['fine_applicable'] and (gold['scope']!='research' or gold['status']!='broad_only'):raise ValueError('Only research broad_only can leave the fine denominator')
    if gold['status'] == 'broad_only':
        if gold['fine_applicable'] or gold['scope']!='research':raise ValueError('Broad-only requires research and fine_applicable=false')
        parents={t.get('parent_id') for t in taxonomy['topics']}
        if any(not labels or any(label not in parents for label in labels) for labels in alternatives):raise ValueError('Broad-only requires explicit parent labels')
    if gold['status'] in {'insufficient_evidence','taxonomy_gap'} and any(alternatives):raise ValueError('Required abstention gold cannot have research labels')
    return gold

def identity_aliases(item):
    aliases = {canonical_id(item)}
    text = ' '.join(str(item.get(k, '')) for k in ('url', 'arxiv_id', 'doi', 'pdf_url'))
    for ident in re.findall(r'(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?', text): aliases.add('arxiv:' + ident)
    for ident in re.findall(r'10\.\d{4,9}/[^\s?#]+', text, re.I): aliases.add('doi:' + ident.rstrip('/').lower())
    title = title_alias(item)
    if title: aliases.add('title:' + title)
    return aliases

def split_records(dev_items, unseen_items):
    """Union all standard IDs/title aliases before splitting; audited groups stay dev."""
    entries = [('dev', item) for item in dev_items] + [('holdout', item) for item in unseen_items]
    parents = list(range(len(entries))); aliases = {}
    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]; x = parents[x]
        return x
    for i, (_, item) in enumerate(entries):
        for alias in identity_aliases(item):
            if alias in aliases: parents[find(i)] = find(aliases[alias])
            aliases[alias] = i
    groups = {}
    for i, entry in enumerate(entries): groups.setdefault(find(i), []).append(entry)
    records = []
    for group in groups.values():
        split = 'dev' if any(s == 'dev' for s, _ in group) else 'holdout'
        item = min((item for s, item in group if s == split), key=lambda item: (canonical_id(item),item['id']))
        all_aliases = set().union(*(identity_aliases(item) for _, item in group))
        public_aliases = sorted(a for a in all_aliases if not a.startswith('title:'))
        records.append({'id':item['id'], 'canonical_id':canonical_id(item), 'identity_aliases':public_aliases, 'split':split, 'item':item, 'gold':None})
    records.sort(key=lambda r:r['canonical_id'])
    random.Random(SEED).shuffle(records)
    return records

def leakage_check(records, private_references=(), overrides=()):
    """Returns only counts, never emits private identity/title lists."""
    holdout = [r for r in records if r['split']=='holdout']
    dev = [r for r in records if r['split']=='dev']
    private_aliases = set()
    for item in private_references:
        try: private_aliases |= identity_aliases(item)
        except ValueError:
            if title_alias(item): private_aliases.add('title:' + title_alias(item))
    def row_aliases(row):
        return identity_aliases(row['item']) | set(row.get('identity_aliases', []))
    dev_aliases = set().union(*(row_aliases(r) for r in dev)) if dev else set()
    over = set(overrides)
    return {'dev_group_overlap':sum(bool(row_aliases(r) & dev_aliases) for r in holdout),
            'private_reference_overlap':sum(bool(row_aliases(r) & private_aliases) for r in holdout),
            'override_overlap':sum(r['id'] in over for r in holdout)}

def exclude_holdout_references(records, references):
    """Filter private references in memory before classification; never persist output."""
    holdout_aliases = set()
    for row in records:
        if row['split'] == 'holdout':
            holdout_aliases |= identity_aliases(row['item']) | set(row.get('identity_aliases', []))
    kept = []
    for reference in references:
        try: aliases = identity_aliases(reference)
        except ValueError:
            aliases = {'title:' + title_alias(reference)} if title_alias(reference) else set()
        if not aliases & holdout_aliases: kept.append(reference)
    return kept, {'input_reference_n':len(references),'excluded_holdout_reference_n':len(references)-len(kept)}

def prf(tp, fp, fn):
    p = tp/(tp+fp) if tp+fp else None; r = tp/(tp+fn) if tp+fn else None
    f = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
    return {'tp':tp,'fp':fp,'fn':fn,'precision':p,'recall':r,'f1':f}

def best_set(pred, alternatives):
    scored = []
    for alt in alternatives:
        gold=set(alt); m=prf(len(pred&gold),len(pred-gold),len(gold-pred))
        scored.append((-(m['f1'] if m['f1'] is not None else 1),tuple(sorted(gold)),gold))
    return min(scored,key=lambda x:x[:2])[2]

def evaluate(records, predictions, taxonomy, split='holdout', baseline_f1=None, bootstrap=1000):
    rows=[r for r in records if r['split']==split]
    if not rows: raise ValueError('No evaluation rows')
    roots={t['id'] for t in taxonomy['topics'] if not t.get('parent_id')}
    byid={p['id']:p for p in predictions}
    if len(byid)!=len(predictions): raise ValueError('Duplicate predictions')
    confusions={name:Counter() for name in ('scope','status','content_kind')}; counts=Counter(); perclass={}; root_counts={root:Counter() for root in roots}; kind_gold=Counter(); kind_tp=Counter(); kind_pred=Counter(); observations=[]
    for row in rows:
        g=validate_gold(row['gold'],taxonomy)
        if row['id'] not in byid: raise ValueError('Missing prediction')
        p=byid[row['id']]; pred=specific(p.get('topic_leaf_ids',[]),taxonomy); gold=best_set(pred,g['acceptable_topic_sets'])
        rp=ancestors(pred,taxonomy)&roots; rg=ancestors(gold,taxonomy)&roots
        for key,val in [('root_tp',len(rp&rg)),('root_fp',len(rp-rg)),('root_fn',len(rg-rp))]: counts[key]+=val
        for root in roots:
            rc=root_counts[root]; rc['support']+=root in rg; rc['tp']+=root in rp&rg; rc['fp']+=root in rp-rg; rc['fn']+=root in rg-rp
        sample=(0,0,0)
        if g['fine_applicable']:
            sample=(len(pred&gold),len(pred-gold),len(gold-pred)); counts['fine_n']+=1
            for key,val in zip(('tp','fp','fn'),sample): counts[key]+=val
            for label in pred|gold:
                c=perclass.setdefault(label,Counter()); c['support']+=label in gold;c['tp']+=label in pred&gold;c['fp']+=label in pred-gold;c['fn']+=label in gold-pred
        else:
            counts['broad_n']+=1
            counts['broad_over']+=bool(pred-ancestors(gold,taxonomy))
        observations.append({'fine':sample,'root':(len(rp&rg),len(rp-rg),len(rg-rp)),'domain':(len(set(p.get('domain_facets',[]))&set(g['domain_facets'])),len(set(p.get('domain_facets',[]))-set(g['domain_facets'])),len(set(g['domain_facets'])-set(p.get('domain_facets',[]))))})
        for key in confusions:confusions[key][(g[key],str(p.get(key,'unknown')))]+=1
        counts['gold_status_'+g['status']]+=1;counts['gold_scope_'+g['scope']]+=1
        if g['scope']=='non_research': counts['nonresearch_n']+=1;counts['leak']+=bool(pred)
        if g['scope']=='research' and g['status'] not in {'taxonomy_gap','insufficient_evidence'}:
            counts['eligible_n']+=1;counts['covered']+=bool(pred)
        kind_gold[g['content_kind']]+=1;kind_pred[p.get('content_kind','unknown')]+=1
        if p.get('content_kind')==g['content_kind']: kind_tp[g['content_kind']]+=1
        dg=set(g['domain_facets']);dp=set(p.get('domain_facets',[]))
        counts['domain_tp']+=len(dp&dg);counts['domain_fp']+=len(dp-dg);counts['domain_fn']+=len(dg-dp)
    fine=prf(counts['tp'],counts['fp'],counts['fn']);root=prf(counts['root_tp'],counts['root_fp'],counts['root_fn'])
    ratio=lambda a,b:counts[a]/counts[b] if counts[b] else None
    kind_scores={k:{'support':kind_gold[k],**prf(kind_tp[k],kind_pred[k]-kind_tp[k],kind_gold[k]-kind_tp[k])} for k in kind_gold.keys()|kind_pred.keys()}
    supported=[v['f1'] for v in kind_scores.values() if v['support'] and v['f1'] is not None]
    kind_macro=sum(supported)/len(supported) if supported else None
    class_scores={k:{'support':v['support'],**prf(v['tp'],v['fp'],v['fn'])} for k,v in perclass.items()}
    macro_values=[v['f1'] for v in class_scores.values() if v['support']>=5 and v['f1'] is not None]
    root_scores={k:{'support':v['support'],**prf(v['tp'],v['fp'],v['fn'])} for k,v in root_counts.items()}
    domain=prf(counts['domain_tp'],counts['domain_fp'],counts['domain_fn'])
    metric={'n':len(rows),'fine_n':counts['fine_n'],'fine':fine,'root':root,'root_facets':root_scores,'fine_classes':class_scores,'fine_macro_support_ge5':sum(macro_values)/len(macro_values) if macro_values else None,'content_kind':kind_scores,'content_kind_macro_f1':kind_macro,'domain':domain,'nonresearch_n':counts['nonresearch_n'],'nonresearch_leak':ratio('leak','nonresearch_n'),'eligible_research_n':counts['eligible_n'],'research_coverage':ratio('covered','eligible_n'),'broad_n':counts['broad_n'],'broad_overspecific':ratio('broad_over','broad_n')}
    metric['confusion_matrices']={name:[{'gold':g,'predicted':p,'n':n} for (g,p),n in sorted(matrix.items())] for name,matrix in confusions.items()}
    metric['gold_status_support']={key.removeprefix('gold_status_'):value for key,value in counts.items() if key.startswith('gold_status_')}
    metric['gold_scope_support']={key.removeprefix('gold_scope_'):value for key,value in counts.items() if key.startswith('gold_scope_')}
    rng=random.Random(SEED); samples={name:{'precision':[],'recall':[]} for name in ('fine','root','domain')}
    for _ in range(bootstrap):
        totals={name:[0,0,0] for name in samples}
        for _ in rows:
            observation=rng.choice(observations)
            for name in samples:
                for j,value in enumerate(observation[name]):totals[name][j]+=value
        for name in samples:
            score=prf(*totals[name])
            for key in samples[name]:
                if score[key] is not None:samples[name][key].append(score[key])
    for name,values in samples.items():
        metric[name+'_bootstrap_ci95']={k:[sorted(v)[int(.025*(len(v)-1))],sorted(v)[int(.975*(len(v)-1))]] if v else None for k,v in values.items()}
    ge=lambda v,t:v is not None and v>=t
    le=lambda v,t:v is not None and v<=t
    gates={'holdout_n':len(rows)>=60,'dev_n':sum(r['split']=='dev' for r in records)>=88,'root_support':all(v['support']>=10 for v in root_scores.values()),'nonresearch_support':counts['nonresearch_n']>=20,'root_precision':ge(root['precision'],.95),'fine_precision':ge(fine['precision'],.90),'fine_recall':ge(fine['recall'],.75),'fine_f1':ge(fine['f1'],.80),'nonresearch_leak':le(metric['nonresearch_leak'],.05),'research_coverage':ge(metric['research_coverage'],.70),'kind_f1':ge(kind_macro,.90),'domain_f1':ge(domain['f1'],.85),'broad_overspecific':counts['broad_n']==0 or le(metric['broad_overspecific'],.05),'baseline_improvement':baseline_f1 is not None and ge(fine['f1'],baseline_f1 if baseline_f1>=.95 else baseline_f1+.05),'root_nonregression':False,'private_exclusion_verified':False,'independent_review_verified':False}
    return {'schema_version':1,'metrics':metric,'gates':gates,'quality_pass':all(gates.values()),'note':'External evidence gates remain false until independent receipts are attached.'}

CONTENT_KIND_ALIASES = {'web:paper':'paper','web:technical_report':'technicalreport','web:model_release':'modelrelease','web:engineering_update':'engineeringupdate','web:organization_policy':'organizationpolicy'}

def adapt_prediction(item):
    """Normalize the website namespace to the frozen evaluation contract."""
    kind = item.get('content_kind','unknown')
    return {'id':item['id'],'topic_leaf_ids':list(item.get('topic_leaf_ids',[])),
            'scope':item.get('scope',item.get('topic_scope','unknown')),
            'status':item.get('status',item.get('topic_status','pending')),
            'content_kind':CONTENT_KIND_ALIASES.get(kind,kind),
            'domain_facets':list(item.get('domain_facets',[]))}

def align_dataset_taxonomy(dataset, taxonomy):
    """Return a public copy with frozen old IDs resolved through registry aliases."""
    import copy
    data=copy.deepcopy(dataset);aliases=taxonomy.get('aliases',{})
    known={t['id'] for t in taxonomy['topics']}
    def resolve(ident):
        seen=set()
        while ident in aliases:
            if ident in seen:raise ValueError('Cyclic topic alias')
            seen.add(ident);ident=aliases[ident]
        if ident not in known:raise ValueError('Frozen evaluation topic cannot be migrated')
        return ident
    for row in data['records']:
        if row.get('gold'):
            row['gold']['acceptable_topic_sets']=[sorted({resolve(t) for t in group}) for group in row['gold']['acceptable_topic_sets']]
    data['taxonomy']=copy.deepcopy(taxonomy)
    return data


def verify_external_receipts(evidence, dataset, predictions):
    """Bind exclusion to the exact normalized prediction artifact being scored."""
    data_hash=digest(dataset);prediction_hash=digest([adapt_prediction(p) for p in predictions])
    gates={}
    for name in ('private_exclusion_verified','independent_review_verified'):
        receipt=evidence.get(name,{})
        valid=isinstance(receipt,dict) and receipt.get('dataset_sha256')==data_hash and isinstance(receipt.get('reviewer'),str) and bool(receipt['reviewer'].strip()) and receipt.get('pass') is True
        if name=='private_exclusion_verified':valid=valid and receipt.get('predictions_sha256')==prediction_hash
        gates[name]=bool(valid)
    return gates
