"""Paper-landscape public contract and recovery; no network or model calls."""
import math,sys,unittest
from pathlib import Path
from unittest.mock import patch
SITE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SITE))
from landscape import landscape,paper_area

def paper(i,**fields):
 return {'id':'p'+str(i),'title':'Scientific publication','excerpt':'','type':'paper','url':'https://example.org/p/'+str(i),'first_seen':'2020-01-03T00:00:00Z',**fields}
def archive(items):return {'generated_at':'2020-02-01T12:00:00Z','items':items}
class LandscapeContract(unittest.TestCase):
 def test_paper_scope_and_pending_boundary(self):
  rows=[paper(1,published_at='2020-01-01T00:00:00Z'),paper(2,journal_relevance={'status':'pending'}),paper(3,topic_scope='non_research'),paper(4,type='report'),paper(5,type='release'),paper(6,journal_relevance={'status':'relevant'})]
  result=landscape(archive(rows));self.assertEqual({p['id'] for p in result['papers']},{'p1','p6'});self.assertEqual(result['excluded_pending'],1)
 def test_missing_publication_day_stays_unknown_and_old_snapshot_bounds_dates(self):
  result=landscape(archive([paper(1),paper(2,published_at='2021-01-01T00:00:00Z'),paper(3,published_at='not-a-date'),paper(4,published_at='2020-01-31T18:00:00Z')]))
  rows={p['id']:p for p in result['papers']};self.assertEqual(result['as_of_date'],'2020-02-01');self.assertIsNone(rows['p1']['date']);self.assertIsNone(rows['p2']['date']);self.assertIsNone(rows['p3']['date']);self.assertEqual(rows['p4']['date'],'2020-02-01');self.assertEqual(len(rows),4)
 def test_explicit_scientific_application_beats_generic_method(self):
  for title,expected in [('Graph neural networks predict interatomic potentials for alloys','materials'),('Machine learning for protein structure prediction','biology'),('Language models for retrosynthesis and reaction prediction','chemistry')]:
   with self.subTest(title=title):self.assertEqual(paper_area(title,'This work studies machine learning models.'),expected)
 def test_small_samples_keep_readable_papers_without_invented_clusters(self):
  for count in (0,1,11):
   with self.subTest(count=count):
    result=landscape(archive([paper(i) for i in range(count)]));self.assertEqual(len(result['papers']),count);self.assertEqual(result['clusters'],[]);self.assertEqual(result['method']['status'],'insufficient');self.assertTrue(all(p['cluster'] is None and p['x'] is None and p['y'] is None for p in result['papers']))
 def test_real_clustering_output_has_resolvable_membership_and_finite_projection(self):
  themes=[('alloys crystal electrolyte electrode ceramics polymer battery interatomic potentials','materials'),('protein antibody genome transcriptome enzyme dna biomolecular drug discovery','biology'),('robot manipulation dexterous scene camera video embodied navigation','embodied')]
  rows=[paper(group*12+i,title=text,excerpt=('Public '+text+' experimental observations. ')*3,published_at='2020-01-01T00:00:00Z') for group,(text,_) in enumerate(themes) for i in range(12)]
  result=landscape(archive(rows));self.assertEqual({p['id'] for p in result['papers']},{p['id'] for p in rows});self.assertEqual(result['method']['status'],'ok');clusters={c['id']:c for c in result['clusters']};self.assertEqual(len(clusters),len(result['clusters']));self.assertGreaterEqual(len(clusters),2)
  areas={a['id'] for a in result['areas']}
  for c in clusters.values():
   self.assertTrue(c['label']);self.assertTrue(c['terms']);self.assertGreaterEqual(sum(p['cluster']==c['id'] for p in result['papers']),3)
   for coordinate in (c['x'],c['y']):self.assertTrue(math.isfinite(coordinate));self.assertTrue(0<=coordinate<=1)
  for p in result['papers']:
   self.assertIn(p['area'],areas)
   if p['cluster'] is None:self.assertIsNone(p['x']);self.assertIsNone(p['y'])
   else:
    self.assertIn(p['cluster'],clusters)
    for coordinate in (p['x'],p['y']):self.assertTrue(math.isfinite(coordinate));self.assertTrue(0<=coordinate<=1)
 def test_optional_clustering_runtime_failure_keeps_paper_reader_usable(self):
  with patch('landscape.cluster_papers',side_effect=ImportError('Synthetic missing optional runtime')):result=landscape(archive([paper(1)]))
  self.assertEqual(result['method']['status'],'unavailable');self.assertEqual(result['clusters'],[]);self.assertEqual(result['papers'][0]['id'],'p1');self.assertIsNone(result['papers'][0]['cluster'])
class LandscapeAreaRecovery(unittest.TestCase):
    @staticmethod
    def classify(title, excerpt="", labels=(), topics=()):
        row = paper(1, title=title, excerpt=excerpt, topic_labels=list(labels))
        data = {**archive([row]), "taxonomy": {"topics": list(topics)}}
        return landscape(data)["papers"][0]["area"]

    def test_reuses_corroborated_fine_topic_on_a_previously_unmapped_paper(self):
        topic = {
            "id": "training", "path": "display name can change",
            "catalog_path": "02 AI方法 / 学习、训练与优化 / 预训练与后训练",
        }
        label = {"id": "training", "method": "local_lexical_v2", "confidence": "medium"}
        self.assertEqual(
            self.classify("Learning strategies under limited supervision", "We study pretraining.", [label], [topic]),
            "models",
        )
        self.assertEqual(
            self.classify("Learning strategies under limited supervision", "We study pretraining.", [label], [{**topic, "retired": True}]),
            "other",
        )

    def test_video_editing_task_is_primary_over_post_training_method(self):
        topic = {"id": "training", "path": "02 AI方法 / 学习、训练与优化 / 预训练与后训练"}
        label = {"id": "training", "method": "local_lexical_v2", "confidence": "medium"}
        self.assertEqual(
            self.classify(
                "Improving and Expanding Video Editing Capabilities Without Videos",
                "We propose post-training to improve editing capabilities.", [label], [topic],
            ),
            "embodied",
        )

    def test_unsupported_and_conflicting_signals_remain_in_other(self):
        topic = {"id": "2d", "path": "01 材料研究 / 二维材料"}
        label = {"id": "2d", "method": "local_lexical_v2", "confidence": "medium"}
        self.assertEqual(
            self.classify("Evaluating the Transfer of Co-Evolved Communication from 2D to 3D Simulation",
                          "We test communication in 2D and 3D.", [label], [topic]),
            "other",
        )
        self.assertEqual(self.classify("Hydrogel scaffolds for brain organoid engineering"), "other")

    def test_prior_clear_assignment_keeps_the_existing_area(self):
        topic = {"id": "generation", "path": "02 AI方法 / 生成模型 / 扩散与流模型"}
        label = {"id": "generation", "method": "manual", "confidence": "exact"}
        self.assertEqual(
            self.classify("Alloy design with language models", "", [label], [topic]), "materials",
        )


if __name__ == "__main__":
    unittest.main()
