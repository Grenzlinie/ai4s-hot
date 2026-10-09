"""Independent API-shape and alias-integrity regressions, synthetic data only."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('independent_identity', ROOT/'site/topics_identity.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)
CONFIG = {'id_salt':'synthetic-test-salt-with-at-least-32-bytes','publish_root_keys':['ROOT']}

def rows(parent=None):
    return [{'key':'ROOT','data':{'name':'Research','parentCollection':parent}},
            {'key':'CHILD','data':{'name':'Methods','parentCollection':'ROOT'}}]

class IndependentIdentity(unittest.TestCase):
    def test_zotero_root_false_is_normalized_as_root(self):
        # Native Zotero Web API represents root parentCollection as false.
        expected, _ = identity.registry_from_collections(rows(None), {}, CONFIG)
        actual, _ = identity.registry_from_collections(rows(False), {}, CONFIG)
        self.assertEqual(actual, expected)

    def test_previous_alias_cannot_redirect_a_current_stable_identity(self):
        previous, mapping = identity.registry_from_collections(rows(), {}, CONFIG)
        poisoned = copy.deepcopy(previous)
        poisoned['aliases'] = {mapping['ROOT']:mapping['CHILD']}
        with self.assertRaises(identity.IdentityError):
            identity.registry_from_collections(rows(), poisoned, CONFIG)
        self.assertEqual(previous['aliases'], {})

    def test_false_child_parent_is_not_an_orphan(self):
        source = rows(False)
        source.append({'key':'UNPUBLISHED','data':{'name':'Personal','parentCollection':False}})
        public, mapping = identity.registry_from_collections(source, {}, CONFIG)
        self.assertEqual(set(mapping), {'ROOT','CHILD'})
        self.assertEqual(len(public['topics']), 2)

if __name__=='__main__':unittest.main()
