"""Optional CPU-only E5 candidates; private embeddings exist only in RAM."""
import os
from topics_catalog import definition_for_topic
MODEL='intfloat/multilingual-e5-small'
REVISION='614241f622f53c4eeff9890bdc4f31cfecc418b3'

class SemanticCandidates:
    def __init__(self, corpus, topics, catalog):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(max(1,min(4,os.cpu_count() or 1)))
        self.model=SentenceTransformer(MODEL,revision=REVISION,device='cpu',trust_remote_code=False)
        self.model.max_seq_length=512
        definitions={r['path']:r for r in catalog['topics']}
        self.rows=[{'topics':[t['id']],'text':' '.join(definition_for_topic(t,definitions).get('synonyms',[]))} for t in topics]
        self.rows+=corpus
        self.vectors=self.encode([r['text'] for r in self.rows])

    def encode(self,texts):
        import numpy as np
        chunks=[];positions=[]
        for i,text in enumerate(texts):
            # Tokenize locally, keep at most two bounded 500-token windows.
            ids=self.model.tokenizer.encode(text,add_special_tokens=False,truncation=True,max_length=1000)
            parts=[ids[:500],ids[500:1000]] if len(ids)>500 else [ids]
            for part in parts:
                positions.append(i);chunks.append('query: '+self.model.tokenizer.decode(part))
        encoded=self.model.encode(chunks,batch_size=16,normalize_embeddings=True,show_progress_bar=False)
        output=[]
        for i in range(len(texts)):
            v=np.mean([encoded[j] for j,p in enumerate(positions) if p==i],axis=0)
            output.append(v/max(np.linalg.norm(v),1e-12))
        return np.array(output)

    def score(self,text):
        values=(self.encode([text]) @ self.vectors.T)[0]
        scores={}
        for row,value in zip(self.rows,values):
            for topic in row['topics']: scores[topic]=max(scores.get(topic,-1),float(value))
        return scores
