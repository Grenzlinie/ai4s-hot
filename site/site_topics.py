"""Compatibility boundary for legacy v1 and production v2 topic classification."""
import os
from pyzotero import zotero
from topics_v1 import collection_tree,topic_ancestors,tokens,title_key,normalize
import topics_v1


def read_taxonomy(previous,now):
    if os.environ.get('TOPICS_MODE','v1')=='v1': return topics_v1.read_taxonomy(previous,now)
    library,key=os.environ.get('ZOTERO_ID'),os.environ.get('ZOTERO_KEY')
    if not library or not key: return {**previous,'status':'unconfigured'},[]
    try:
        from pyzotero import zotero
        from topics_identity import load_private_config,registry_from_collections
        client=zotero.Zotero(library,'user',key)
        config=load_private_config()
        collections=client.everything(client.collections())
        taxonomy,key_ids=registry_from_collections(collections,previous,config)
        corpus=[]
        for record in client.everything(client.top(itemType='-attachment')):
            row=record['data']
            if row.get('itemType') in ('attachment','note','annotation'): continue
            ids=sorted({key_ids[k] for k in row.get('collections',[]) if k in key_ids})
            ids=[t for t in ids if not any(t in topic_ancestors([other],taxonomy['topics']) for other in ids if other!=t)]
            if row.get('title') and ids:
                corpus.append({'title':row['title'],'text':row['title']+' '+row.get('abstractNote',''),'topics':ids,'doi':row.get('DOI',''),'url':row.get('url',''),'extra':row.get('extra','')})
        taxonomy.update(last_success=now,method='Local private evidence; public definitions; independent facets')
        return taxonomy,corpus
    except Exception as error:
        return {**previous,'status':'stale' if previous.get('topics') else 'error','error_type':type(error).__name__},[]


def classify(items,taxonomy,corpus):
    if os.environ.get('TOPICS_MODE','v1')=='v1': return topics_v1.classify(items,taxonomy,corpus)
    if taxonomy.get('status') not in ('ok','active'):
        return {'status':'unavailable','classified':0}
    from topics_classifier import classify_v2
    return classify_v2(items,taxonomy,corpus)
