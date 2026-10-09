"""Offline local taxonomy/classifier checks; synthetic Zotero records only."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SITE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('topics_under_test',SITE/'site_topics.py')
topics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(topics)


def collection(key,name,parent=None):
    return {'key':key,'data':{'key':key,'name':name,'parentCollection':parent},'links':{'private':'PRIVATE_LINK'}}


ROWS = [collection('PRIVATE_ROOT','Science'),collection('PRIVATE_CHILD','Materials','PRIVATE_ROOT'),collection('PRIVATE_LEAF','Potentials','PRIVATE_CHILD'),collection('PRIVATE_BIO','Proteins','PRIVATE_ROOT'),collection('PRIVATE_SKIP','00 Inbox'),collection('PRIVATE_SKIP_CHILD','Hidden','PRIVATE_SKIP')]


class TopicAcceptance(unittest.TestCase):
    def setUp(self):
        self.tree = topics.collection_tree(ROWS)
        self.by_name = {t['name']:t for t in self.tree}
        self.taxonomy = {'topics':self.tree,'version':'test-version'}
        self.item = {'id':'paper1','title':'Potential models','excerpt':'ML potential'}
        self.leaf = self.by_name['Potentials']['id']
        self.bio = self.by_name['Proteins']['id']
        self.corpus = [
            {'title':'PRIVATE_REFERENCE Potential modeling','text':'PRIVATE_ABSTRACT crystal energy atomistic potentials molecular dynamics','topics':[self.leaf]},
            {'title':'Protein folding','text':'Protein folding sequence enzyme biology','topics':[self.bio]},
        ]

    def test_hierarchy_excludes_00_subtree_and_never_exports_private_keys(self):
        self.assertEqual(set(self.by_name),{'Science','Materials','Potentials','Proteins'})
        self.assertEqual(self.by_name['Potentials']['path'],'Science / Materials / Potentials')
        self.assertEqual(self.by_name['Potentials']['parent_id'],self.by_name['Materials']['id'])
        self.assertEqual(self.by_name['Materials']['parent_id'],self.by_name['Science']['id'])
        self.assertNotIn('PRIVATE',json.dumps(self.tree))
        self.assertEqual(self.tree,topics.collection_tree(list(reversed(ROWS))))

    def test_tree_cycles_and_unknown_ancestor_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            topics.collection_tree([collection('A','A','B'),collection('B','B','A')])
        with self.assertRaises(ValueError):
            topics.topic_ancestors(['unknown'],self.tree)
        self.assertEqual(topics.topic_ancestors([self.leaf,self.leaf],self.tree),topics.topic_ancestors([self.leaf],self.tree))

    def test_exact_multi_label_matching_adds_ancestors_and_caches(self):
        corpus = [{'title':self.item['title'],'text':'PRIVATE_REFERENCE abstract','topics':[self.leaf,self.bio]}]
        status = topics.classify([self.item],self.taxonomy,corpus)
        self.assertEqual(status['classified'],1)
        self.assertEqual(set(self.item['topic_leaf_ids']),{self.leaf,self.bio})
        self.assertEqual(set(self.item['topic_ids']),{t['id'] for t in self.tree})
        self.assertEqual(self.item['topic_method'],'zotero_match')
        cached = topics.classify([self.item],self.taxonomy,corpus)
        self.assertEqual(cached['classified'],0)
        self.assertRegex(self.item['topic_version'],r'^[0-9a-f]{64}$')
        self.assertNotIn('PRIVATE',json.dumps(self.item))

    def test_local_similarity_is_deterministic_and_uses_matching_reference(self):
        item = {'id':'new','title':'Atomistic crystal energy','excerpt':'molecular dynamics potentials'}
        second = copy.deepcopy(item)
        topics.classify([item],self.taxonomy,self.corpus)
        topics.classify([second],self.taxonomy,self.corpus)
        self.assertEqual(item,second)
        self.assertEqual(item['topic_leaf_ids'],[self.leaf])
        self.assertEqual(item['topic_method'],'local_similarity')
        self.assertNotIn('PRIVATE',json.dumps(item))

    def test_unmatched_item_stays_unclassified_and_is_cached(self):
        item = {'id':'other','title':'Jazz concert ticket','excerpt':'music trumpet improvisation'}
        topics.classify([item],self.taxonomy,self.corpus)
        self.assertEqual(item['topic_ids'],[])
        self.assertEqual(item['topic_leaf_ids'],[])
        self.assertEqual(topics.classify([item],self.taxonomy,self.corpus)['classified'],0)

    def test_empty_token_titles_do_not_create_false_exact_match(self):
        corpus = [{'title':'AI','text':'Protein enzyme biology','topics':[self.bio]}]
        item = {'id':'other','title':'The model','excerpt':'unrelated concert'}
        topics.classify([item],self.taxonomy,corpus)
        self.assertEqual(item['topic_ids'],[])
        self.assertEqual(item['topic_method'],'local_similarity')
        punctuation = {'id':'punctuation','title':'---','excerpt':'unrelated concert'}
        topics.classify([punctuation],self.taxonomy,[{'title':'...','text':'protein biology','topics':[self.bio]}])
        self.assertEqual(punctuation['topic_ids'],[])
        self.assertEqual(punctuation['topic_method'],'local_similarity')

    def test_exact_titles_keep_stopwords_but_normalize_case_and_punctuation(self):
        corpus = [{'title':'The protein model','text':'protein biology','topics':[self.bio]}]
        different = {'id':'different','title':'A protein model','excerpt':'protein biology'}
        normalized = {'id':'normalized','title':'  THE protein model!  ','excerpt':'protein biology'}
        topics.classify([different,normalized],self.taxonomy,corpus)
        self.assertEqual(different['topic_method'],'local_similarity')
        self.assertEqual(normalized['topic_method'],'zotero_match')

    def test_empty_corpus_preserves_existing_labels_and_version(self):
        self.item.update(topic_leaf_ids=[self.leaf],topic_ids=topics.topic_ancestors([self.leaf],self.tree),topic_version='old')
        before = copy.deepcopy(self.item)
        result = topics.classify([self.item],self.taxonomy,[])
        self.assertEqual(self.item,before)
        self.assertEqual(result['status'],'unavailable')

    def test_empty_taxonomy_does_not_mutate_existing_item(self):
        before = copy.deepcopy(self.item)
        result = topics.classify([self.item],{'topics':[]},self.corpus)
        self.assertEqual(result['status'],'unconfigured')
        self.assertEqual(self.item,before)

    def test_zotero_failure_retains_previous_tree_without_exception_contents(self):
        previous = {**self.taxonomy,'last_success':'2026-10-01T00:00:00Z'}
        with patch.dict(topics.os.environ,{'ZOTERO_ID':'123','ZOTERO_KEY':'SYNTHETIC_KEY'}),patch.object(topics.zotero,'Zotero',side_effect=RuntimeError('PRIVATE_KEY')):
            result,corpus = topics.read_taxonomy(previous,'now')
        self.assertEqual(result['topics'],previous['topics'])
        self.assertEqual(result['last_success'],previous['last_success'])
        self.assertEqual(result['status'],'stale')
        self.assertEqual(corpus,[])
        self.assertNotIn('PRIVATE',json.dumps(result))

    def test_read_taxonomy_public_result_excludes_records_keys_and_private_corpus(self):
        records = [
            {'data':{'title':'PRIVATE_REFERENCE title','abstractNote':'PRIVATE_ABSTRACT text','collections':['PRIVATE_ROOT','PRIVATE_CHILD','PRIVATE_LEAF'],'itemType':'journalArticle'}},
            {'data':{'title':'PRIVATE_NOTE','collections':['PRIVATE_LEAF'],'itemType':'note'}},
            {'data':{'title':'PRIVATE_ATTACHMENT','collections':['PRIVATE_LEAF'],'itemType':'attachment'}},
            {'data':{'title':'PRIVATE_EXCLUDED','collections':['PRIVATE_SKIP'],'itemType':'journalArticle'}},
        ]
        client = SimpleNamespace(collections=lambda:ROWS,top=lambda **kwargs:records,everything=lambda records:records)
        with patch.dict(topics.os.environ,{'ZOTERO_ID':'123','ZOTERO_KEY':'SYNTHETIC_KEY'}),patch.object(topics.zotero,'Zotero',return_value=client):
            public,corpus = topics.read_taxonomy({},'now')
        self.assertEqual(public['status'],'ok')
        self.assertNotIn('PRIVATE',json.dumps(public))
        self.assertNotIn('SYNTHETIC_KEY',json.dumps(public))
        self.assertEqual(len(corpus),1)
        self.assertEqual(corpus[0]['topics'],[self.leaf])
        self.assertIn('PRIVATE_ABSTRACT',corpus[0]['text'])
        self.assertRegex(public['version'],r'^[0-9a-f]{64}$')


if __name__=='__main__':
    unittest.main()
