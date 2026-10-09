"""Public catalog schema regressions, synthetic invalid inputs only."""
import copy,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'site'))
from topics_catalog import validate_catalog,load_catalog

def fixture():
    return {'version':'synthetic-v1','topics':[{'path':'Root','definition':'Public synthetic definition','facet':'Root','definition_status':'authored','synonyms':['material'],'include':['scientific'],'exclude':[]}],'web_facets':{'content_kind':['web:paper'],'domain':['web:materials']}}

class CatalogAcceptance(unittest.TestCase):
    def test_actual_public_catalog_53_valid(self):self.assertEqual(len(load_catalog()['topics']),53)
    def test_private_unknown_fields_rejected_without_value_in_error(self):
        for level in ('root','topic','facet'):
            p=fixture();target=p if level=='root' else p['topics'][0] if level=='topic' else p['web_facets'];target['private_reference']='PRIVATE_SENTINEL'
            with self.subTest(level=level),self.assertRaises(ValueError) as error:validate_catalog(p)
            self.assertNotIn('PRIVATE_SENTINEL',str(error.exception))
    def test_duplicate_paths_and_missing_definition_rejected(self):
        p=fixture();p['topics'].append(copy.deepcopy(p['topics'][0]))
        with self.assertRaises(ValueError):validate_catalog(p)
        for field in ('path','definition','facet'):
            p=fixture();p['topics'][0][field]='  '
            with self.subTest(field=field),self.assertRaises(ValueError):validate_catalog(p)
    def test_terms_and_rules_are_unique_nonempty_strings(self):
        for field in ('synonyms','include','exclude','rules'):
            for value in ('not a list',[''],[None],['x','x']):
                p=fixture();p['topics'][0][field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_catalog(p)
    def test_status_and_rule_enums_rejected(self):
        p=fixture();p['topics'][0]['definition_status']='machine_guessed'
        with self.assertRaises(ValueError):validate_catalog(p)
        p=fixture();p['topics'][0]['rules']=['unknown_private_rule']
        with self.assertRaises(ValueError):validate_catalog(p)
        p['topics'][0]['rules']=['require_scientific_task','require_acquisition_evidence'];self.assertIs(validate_catalog(p),p)
    def test_website_facets_require_unique_public_ids(self):
        for value in ([],['private:key'],['web:paper','web:paper'],[None]):
            p=fixture();p['web_facets']['content_kind']=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate_catalog(p)

if __name__=='__main__':unittest.main()
