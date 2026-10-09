"""Private in-memory evidence normalization. Never serialize these rows."""
import re
from collections import defaultdict
from topics_v1 import title_key


def arxiv_identifiers(row):
    """Require an explicit field or arXiv prefix; DOI numeric suffixes are not IDs."""
    result=set()
    bare=re.fullmatch(r'\s*(\d{4}\.\d{4,5})(?:v\d+)?\s*',str(row.get('arxiv_id','')),re.I)
    if bare:result.add(bare.group(1))
    text=' '.join(str(row.get(k,'')) for k in ('arxiv_id','url','pdf_url','extra'))
    patterns=(r'(?<![\w/])(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?(?![\w.])',
              r'(?<![\w/])arxiv(?:\s+ID)?\s*:\s*(\d{4}\.\d{4,5})(?:v\d+)?(?![\w.])')
    for pattern in patterns:result.update(re.findall(pattern,text,re.I))
    return result

def identities(row):
    text = ' '.join(str(row.get(k, '')) for k in ('doi', 'DOI', 'arxiv_id', 'url', 'extra'))
    doi = re.search(r'10\.\d{4,9}/[^\s<>"\]]+', text, re.I)
    arxiv = sorted(arxiv_identifiers(row))
    return {k:v for k,v in [('doi',doi.group().rstrip('.,').lower() if doi else None),('arxiv',arxiv[0] if arxiv else None)] if v}


def prepare(corpus):
    rows=sorted(corpus,key=lambda r:(title_key(r.get('title','')),str(sorted(identities(r).items())),str(sorted((k,str(v)) for k,v in r.items()))))
    grouped=[]
    for row in rows:
        ids=identities(row)
        title=title_key(row.get('title',''))
        if not ids and not title: continue
        matches=[g for g in grouped if any(g['identities'].get(k)==v for k,v in ids.items()) or (not ids and not g['identities'] and title_key(g['title'])==title)]
        if not matches:
            grouped.append({**row,'identities':ids,'topics':sorted(set(row['topics']))})
            continue
        target=matches[0]
        for other in [row,*matches[1:]]:
            target['topics']=sorted(set(target['topics'])|set(other['topics']))
            other_ids=other.get('identities',identities(other))
            # A conflicting secondary ID makes title fallback unsafe; retain sentinel.
            for k,v in other_ids.items():
                if k in target['identities'] and target['identities'][k]!=v:
                    target['identity_conflict']=True
                else: target['identities'][k]=v
            if (len(other.get('text','')),other.get('text',''))>(len(target.get('text','')),target.get('text','')): target['text']=other['text']
        for other in matches[1:]: grouped.remove(other)
    return grouped


def exact_match(item, corpus):
    ids = identities(item)
    standard = [r for r in corpus if any(r['identities'].get(k)==v for k,v in ids.items())]
    candidates = standard or [r for r in corpus if title_key(item.get('title','')) and title_key(r.get('title',''))==title_key(item['title'])]
    candidates = [r for r in candidates if not r.get('identity_conflict') and not any(k in r['identities'] and r['identities'][k]!=v for k,v in ids.items())]
    # Ambiguous normalized titles with conflicting canonical identities are not exact.
    canonical = {tuple(sorted(r['identities'].items())) for r in candidates if r['identities']}
    if not standard and len(canonical)>1:
        return []
    return sorted({t for r in candidates for t in r['topics']})
