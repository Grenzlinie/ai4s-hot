"""Regression for an actual issue-cover duplicate seen during abstract recovery."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import journals
class RecoveryQuality(unittest.TestCase):
 def test_energy_materials_cover_is_not_a_second_research_article(self):
  title="Machine Learning Interatomic Potentials for Energy Materials: Architectures, Training Strategies, and Applications"
  self.assertEqual(journals.relevance(title)["status"],"relevant")
  self.assertEqual(journals.relevance(title+" (Adv. Energy Mater. 39/2026)")["status"],"excluded")
