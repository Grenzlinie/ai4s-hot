"""Local lexical candidates with definition cold start and diverse prototypes."""
import math
import re
from collections import Counter,defaultdict
from topics_v1 import tokens,normalize


def phrase_hit(phrase,text):
    return bool(re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',text,re.I)) if re.search('[a-zA-Z]',phrase) else phrase in text


class LexicalCandidates:
    def __init__(self, corpus, topics, catalog):
        self.catalog = {r['path']:r for r in catalog['topics']}
        self.definitions = {t['id']:self.catalog.get(t.get('catalog_path',t['path']),{}) for t in topics}
        docs = [tokens(r['text']) for r in corpus]
        definition_docs = [tokens(' '.join(d.get('synonyms',[]))+ ' '+d.get('definition','')) for d in self.definitions.values()]
        all_docs=docs+definition_docs
        freq=Counter(k for d in all_docs for k in d)
        self.idf={k:math.log((len(all_docs)+1)/(n+1))+1 for k,n in freq.items()}
        self.prototypes=defaultdict(list)
        for row,doc in zip(corpus,docs):
            for t in row['topics']:
                self.prototypes[t].append(self.vector(doc))
        self.definition_vectors={t:self.vector(tokens(' '.join(d.get('synonyms',[])))) for t,d in self.definitions.items()}

    def vector(self, counts):
        return normalize({k:(1+math.log(v))*self.idf[k] for k,v in counts.items() if k in self.idf})

    def score(self,text):
        counts=tokens(text); q=self.vector(counts)
        coverage=sum(n for k,n in counts.items() if k in self.idf)/max(1,sum(counts.values()))
        scores={}
        for t,d in self.definitions.items():
            # Top examples preserve subthemes instead of collapsing to one centroid.
            sims=sorted((sum(v*p.get(k,0) for k,v in q.items()) for p in self.prototypes[t]),reverse=True)[:3]
            sim=sum(sims)/len(sims) if sims else 0
            definition=sum(v*self.definition_vectors[t].get(k,0) for k,v in q.items())
            hits=[s for s in d.get('include',[]) if phrase_hit(s,text)]
            scores[t]={'score':max(sim,definition*.8,min(.85,.42+.12*len(hits)) if hits else 0),'definition_hit':bool(hits),'cold_start':not bool(sims),'public_terms':hits[:3],'rules':d.get('rules',[])}
        return scores,coverage
