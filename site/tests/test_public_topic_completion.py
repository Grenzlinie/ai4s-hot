"""Public broad categories must never invent scientific fine labels."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from topics_public import complete_public_topics, METHOD, GENERAL
from topics_schema import validate_archive
from landscape import recovery_area

class PublicCompletionTests(unittest.TestCase):
    def payload(self, title='A new research observation'):
        return {'schema_version': 2, 'items': [{'id': 'paper', 'title': title, 'type': 'paper', 'excerpt': '', 'topic_leaf_ids': [], 'topic_ids': []}], 'taxonomy': {'topics': []}}

    def test_insufficient_public_evidence_is_general_not_a_fine_guess(self):
        p=self.payload(); complete_public_topics(p); validate_archive(p)
        item=p['items'][0]
        self.assertEqual(item['topic_leaf_ids'], [GENERAL])
        self.assertIsNone(item['topic_labels'][0]['score'])
        self.assertEqual(item['topic_labels'][0]['method'], METHOD)
        self.assertIn('不足', item['topic_labels'][0]['public_reason'])
        original=copy.deepcopy(p); complete_public_topics(p); self.assertEqual(original,p)

    def test_explicit_public_area_and_non_research_kind(self):
        p=self.payload('Protein design with language models')
        p['items'].append({'id':'news','title':'Introducing our model','type':'release'})
        complete_public_topics(p);validate_archive(p)
        self.assertEqual(p['items'][0]['topic_leaf_ids'], ['public:area:biology'])
        self.assertEqual(p['items'][1]['topic_leaf_ids'], ['public:kind:model_release'])

    def test_coarse_receipt_cannot_recover_scientific_evidence(self):
        item={'title':'Unspecified observations','topic_labels':[{'id':'coarse','method':METHOD,'confidence':'high'}]}
        self.assertEqual(recovery_area(item,{'coarse':'materials'}),'other')

    def test_real_fine_label_and_retired_history_are_preserved(self):
        p=self.payload();p['taxonomy']['topics']=[{'id':'fine','name':'Fine','path':'Fine','parent_id':None,'active':True}]
        label={'id':'fine','facet':'fine','method':'manual','score':None,'confidence':'high','status':'classified','public_reason':'Public evidence'}
        p['items'][0].update(topic_labels=[label],topic_leaf_ids=['fine'],topic_ids=['fine'])
        complete_public_topics(p);self.assertEqual(p['items'][0]['topic_labels'],[label])
        p['taxonomy']['topics'][0]['active']=False
        complete_public_topics(p);validate_archive(p)
        self.assertEqual(p['items'][0]['topic_history'],[label])
        self.assertEqual(p['items'][0]['topic_leaf_ids'],[GENERAL])

    def test_collection_sync_cannot_leave_reactivated_coarse_history(self):
        p=self.payload();complete_public_topics(p)
        p['items'][0]['topic_history']=copy.deepcopy(p['items'][0]['topic_labels'])
        for t in p['taxonomy']['topics']: t['active']=False
        complete_public_topics(p);validate_archive(p)
        self.assertEqual(p['items'][0]['topic_history'],[])

    def test_build_migrates_without_mutating_input_snapshot(self):
        from build import build
        with tempfile.TemporaryDirectory() as tmp:
            d=pathlib.Path(tmp)/'data';d.mkdir();p=self.payload()
            original=json.dumps(p);(d/'index.json').write_text(original)
            (d/'daily').mkdir();(d/'daily'/'snapshot.json').write_text(original)
            (d/'daily'/'ids.json').write_text('{"item_ids":["paper"]}')
            static=pathlib.Path(tmp)/'static';static.mkdir();(static/'schema-support.json').write_text('{"archive_schema_versions":[2]}')
            build(d,pathlib.Path(tmp)/'out',static)
            for name in ['index.json','daily/snapshot.json']:
                out=json.loads((pathlib.Path(tmp)/'out/data'/name).read_text())
                self.assertEqual(out['items'][0]['topic_leaf_ids'],[GENERAL])
            self.assertEqual((d/'index.json').read_text(),original)
            self.assertEqual(json.loads((pathlib.Path(tmp)/'out/data/daily/ids.json').read_text()),{'item_ids':['paper']})

if __name__=='__main__': unittest.main()
