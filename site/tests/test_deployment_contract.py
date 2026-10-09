"""Offline immutable deployment and schema compatibility regressions."""
import copy,hashlib,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'site'))
from build import build
from deployment_manifest import ASSETS,write_manifest
from topics_schema import validate_archive
SHA='a'*40

def archive(version=2):
    return {'schema_version':version,'generated_at':'2026-10-09T00:00:00Z','taxonomy':{'topics':[{'id':'r','parent_id':None},{'id':'a','parent_id':'r'}]},'items':[{'id':'public','topic_leaf_ids':['a'],'topic_ids':['a','r'],'topic_labels':[{'id':'a','facet':'r','method':'local_lexical_v2','score':.5,'confidence':'low','status':'classified','public_reason':'Synthetic public reason'}]}]}
class DeploymentContract(unittest.TestCase):
    def populate(self,tmp,version=2,support=(1,2)):
        root=pathlib.Path(tmp);data=root/'input';static=root/'static';out=root/'output';data.mkdir();static.mkdir()
        (data/'index.json').write_text(json.dumps(archive(version)))
        for asset in ASSETS:(static/asset).write_text('synthetic '+asset)
        if support is not None:(static/'schema-support.json').write_text(json.dumps({'archive_schema_versions':list(support)}))
        return data,static,out
    def test_legacy_frontend_accepts_v1_and_rejects_v2_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            data,static,out=self.populate(tmp,support=None)
            with self.assertRaises(ValueError):build(data,out,static)
            self.assertFalse(out.exists())
            (data/'index.json').write_text(json.dumps(archive(1)));build(data,out,static)
            self.assertEqual(json.loads((out/'data/index.json').read_text())['schema_version'],1)
    def test_new_frontend_builds_both_versions_and_manifest_hashes_exact_bytes(self):
        for version in (1,2):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as tmp:
                data,static,out=self.populate(tmp,version);build(data,out,static);manifest=write_manifest(out,SHA,'b'*40,'c'*40,'rollback')
                self.assertEqual(manifest['archive_sha256'],hashlib.sha256((out/'data/index.json').read_bytes()).hexdigest())
                self.assertEqual(manifest['assets']['app.js'],hashlib.sha256((out/'app.js').read_bytes()).hexdigest());self.assertEqual(manifest['llm_requests'],0);self.assertEqual(manifest['mode'],'rollback')
                self.assertEqual(manifest,json.loads((out/'deployment-manifest.json').read_text()))
    def test_mutable_short_or_shell_refs_rejected_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            data,static,out=self.populate(tmp);build(data,out,static)
            for revision in ('main','a'*39,'A'*40,'$(echo private)','a'*40+'\n'):
                with self.subTest(revision=revision),self.assertRaises(ValueError):write_manifest(out,revision,SHA)
            self.assertFalse((out/'deployment-manifest.json').exists())
    def test_manifest_rejects_nested_private_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            data,static,out=self.populate(tmp,1);build(data,out,static)
            payload=archive(1);payload['taxonomy']['classification']={'private_reference':'PRIVATE_SENTINEL'};(out/'data/index.json').write_text(json.dumps(payload))
            with self.assertRaises(ValueError):write_manifest(out,SHA,SHA)
            self.assertFalse((out/'deployment-manifest.json').exists())
    def test_both_archive_versions_reject_private_fields_before_build(self):
        for version in (1,2):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as tmp:
                data,static,out=self.populate(tmp,version)
                payload=archive(version);payload['taxonomy']['classification']={'private_reference':'PRIVATE_SENTINEL'};(data/'index.json').write_text(json.dumps(payload))
                with self.assertRaises(ValueError) as error:build(data,out,static)
                self.assertNotIn('PRIVATE_SENTINEL',str(error.exception));self.assertFalse(out.exists())
    def test_label_root_score_closure_and_enums_failclosed(self):
        for field,value in [('facet','a'),('score',float('nan')),('score',float('inf')),('score',True),('score',1.1),('score',-.1),('method','remote_llm'),('confidence','certain'),('status','unknown')]:
            p=archive();p['items'][0]['topic_labels'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_archive(p)
        p=archive();p['items'][0]['topic_ids']=['a']
        with self.assertRaises(ValueError):validate_archive(p)
        p=archive();p['items'][0]['topic_labels']*=2
        with self.assertRaises(ValueError):validate_archive(p)
        self.assertIsNotNone(validate_archive(archive()))
if __name__=='__main__':unittest.main()
