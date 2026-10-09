"""Classify public news locally using the user's Zotero collection examples.

Only collection names and inferred labels are serialized. Library item records,
collection keys, vocabulary and reference vectors stay in process memory.
"""
from collections import Counter, defaultdict
import hashlib
import html
import json
import math
import os
import re

from pyzotero import zotero

STOP = set('the and for with from that this have has are was were been into over their our its can via not also these such than which when using used use based new paper study results propose proposed approach method methods model models data performance show shows we on an of in to is by as at or it a'.split())


def collection_tree(collections, key_ids=None):
    by_key = {c['key']: c['data'] for c in collections}
    topics = {}

    def visit(key, seen=()):
        if key in seen:
            raise ValueError('Collection cycle')
        row = by_key[key]
        name = row['name'].strip()
        if re.match(r'^00(?:\s|$)', name):
            return None
        parent = row.get('parentCollection')
        parent_topic = visit(parent, (*seen, key)) if parent in by_key else None
        if parent in by_key and parent_topic is None:
            return None
        path = (parent_topic['path'] + ' / ' if parent_topic else '') + name
        topic_id = 'zt-' + hashlib.sha256(path.encode()).hexdigest()[:12]
        topic = {'id': topic_id, 'name': name, 'path': path,
                 'parent_id': parent_topic['id'] if parent_topic else None}
        topics[topic_id] = topic
        if key_ids is not None:
            key_ids[key] = topic_id
        return topic

    for key in by_key:
        visit(key)
    return sorted(topics.values(), key=lambda t: t['path'])


def read_taxonomy(previous, now):
    library, key = os.environ.get('ZOTERO_ID'), os.environ.get('ZOTERO_KEY')
    if not library or not key:
        return {**previous, 'status': 'unconfigured', 'topics': previous.get('topics', [])}, []
    try:
        client = zotero.Zotero(library, 'user', key)
        key_ids = {}
        topics = collection_tree(client.everything(client.collections()), key_ids)
        if not topics:
            raise ValueError('No usable collections')
        records = client.everything(client.top(itemType='-attachment'))
        corpus = []
        for record in records:
            row = record['data']
            if row.get('itemType') in ('attachment', 'note', 'annotation'):
                continue
            ids = list(dict.fromkeys(key_ids[k] for k in row.get('collections', []) if k in key_ids))
            # A reference saved to both a parent and child supplies the child example.
            ids = [t for t in ids if not any(t in topic_ancestors([other], topics) for other in ids if other != t)]
            title = row.get('title', '')
            if title and ids:
                corpus.append({'title': title, 'text': title + ' ' + row.get('abstractNote', ''), 'topics': ids})
        fingerprint = hashlib.sha256(json.dumps(topics, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        return {'status': 'ok', 'topics': topics, 'version': fingerprint, 'last_success': now,
                'method': 'Local TF-IDF similarity to Zotero collection examples; inferred labels'}, corpus
    except Exception as error:
        return {**previous, 'status': 'stale' if previous.get('topics') else 'error',
                'topics': previous.get('topics', []), 'error_type': type(error).__name__}, []


def topic_ancestors(ids, topics):
    by_id = {t['id']: t for t in topics}
    result = set()
    for topic_id in ids:
        seen = set()
        while topic_id:
            if topic_id in seen or topic_id not in by_id:
                raise ValueError('Invalid topic hierarchy')
            seen.add(topic_id)
            result.add(topic_id)
            topic_id = by_id[topic_id]['parent_id']
    return sorted(result)


def tokens(text):
    text = html.unescape(re.sub(r'<[^>]*>', ' ', text)).lower()
    words = []
    for word in re.findall(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', text):
        if len(word) < 3 or word in STOP:
            continue
        if word.endswith('ies') and len(word) > 5:
            word = word[:-3] + 'y'
        elif word.endswith('s') and not word.endswith(('ss', 'is')) and len(word) > 4:
            word = word[:-1]
        words.append(word)
    for phrase in re.findall(r'[\u4e00-\u9fff]+', text):
        words.extend(phrase[i:i+2] for i in range(len(phrase)-1))
    return Counter(words)


def title_key(text):
    return re.sub(r'[^\w]+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', text))).strip().casefold()


def normalize(vector):
    norm = math.sqrt(sum(x*x for x in vector.values()))
    return {k: v/norm for k, v in vector.items()} if norm else {}


def classify(items, taxonomy, corpus):
    topics = taxonomy.get('topics', [])
    if not topics:
        return {'status': 'unconfigured', 'classified': 0}
    known = {t['id'] for t in topics}
    for p in items:
        p['topic_leaf_ids'] = [t for t in p.get('topic_leaf_ids', []) if t in known]
        p['topic_ids'] = topic_ancestors(p['topic_leaf_ids'], topics)
    if not corpus:
        return {'status': 'unavailable', 'classified': 0}
    document_counts = [tokens(row['text']) for row in corpus]
    frequencies = Counter(term for counts in document_counts for term in counts)
    idf = {term: math.log((len(corpus)+1)/(count+1))+1 for term, count in frequencies.items()}

    def vector(counts):
        return normalize({t: (1+math.log(n))*idf[t] for t, n in counts.items() if t in idf})

    sums = defaultdict(Counter)
    exact = defaultdict(set)
    for row, counts in zip(corpus, document_counts):
        for topic_id in row['topics']:
            if topic_id in known:
                sums[topic_id].update(vector(counts))
                title = title_key(row['title'])
                if title:
                    exact[title].add(topic_id)
    profiles = {t: normalize(counts) for t, counts in sums.items()}
    corpus_version = hashlib.sha256(json.dumps(corpus, sort_keys=True).encode()).hexdigest()
    classified = 0
    for p in items:
        signature = hashlib.sha256(('tfidf-v1' + taxonomy.get('version', '') + corpus_version + p['title'] + p.get('excerpt', '')).encode()).hexdigest()
        if p.get('topic_version') == signature:
            continue
        matches = sorted(exact.get(title_key(p['title']), set()))
        method = 'zotero_match'
        if not matches:
            method = 'local_similarity'
            query = vector(tokens(p['title'] + ' ' + p.get('excerpt', '')))
            scores = sorted(((sum(v*profile.get(t, 0) for t, v in query.items()), topic_id)
                             for topic_id, profile in profiles.items()), reverse=True)
            best = scores[0][0] if scores else 0
            matches = [t for score, t in scores if score >= max(0.15, best*0.85)][:3]
        p.update(topic_leaf_ids=matches, topic_ids=topic_ancestors(matches, topics),
                 topic_version=signature, topic_method=method)
        classified += 1
    return {'status': 'ok', 'classified': classified, 'method': 'local_tfidf',
            'unclassified': sum(not p['topic_ids'] for p in items)}
