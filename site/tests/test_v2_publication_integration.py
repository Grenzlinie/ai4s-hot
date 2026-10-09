"""Actual collector→v2 wrapper/classifier→builder→manifest, mocked I/O only."""
import argparse,contextlib,io,json,os,pathlib,sys,tempfile,unittest
from unittest.mock import MagicMock,patch
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'site'))
import collect,site_topics
from build import build
from deployment_manifest import write_manifest
from topics_schema import validate_archive
class PublicationIntegration(unittest.TestCase):
    def test_v2_publication_has_exact_receipt_and_explicit_unmeasured_quality(self):
        source={'id':'mock','name':'Mock','kind':'fixture','group':'papers','type':'paper'}
        rows=[{'key':'PRIVATE_ROOT','data':{'name':'01 材料研究','parentCollection':False}},{'key':'PRIVATE_CHILD','data':{'name':'多孔框架材料','parentCollection':'PRIVATE_ROOT'}}]
        title='Synthetic MOF scientific experiment'
        refs=[{'data':{'title':title,'abstractNote':'PRIVATE_REFERENCE_ABSTRACT_SENTINEL','collections':['PRIVATE_CHILD'],'itemType':'journalArticle','key':'PRIVATE_ITEM_KEY'}}]
        client=MagicMock();client.everything.side_effect=[rows,refs]
        env={'TOPICS_MODE':'v2','ZOTERO_ID':'synthetic','ZOTERO_KEY':'PRIVATE_KEY_SENTINEL','ZOTERO_TOPIC_CONFIG':json.dumps({'id_salt':'private-synthetic-salt-0123456789abcdef','publish_root_keys':['PRIVATE_ROOT']})}
        def fetch(*args):return [collect.item(source,title,'https://example.org/public',excerpt='A public scientific material experiment uses porous framework samples and reports gas adsorption results.')]
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,env,clear=True),patch.object(site_topics.zotero,'Zotero',return_value=client),patch.dict(collect.COLLECTORS,{'fixture':fetch}),patch.object(collect.requests,'get',side_effect=AssertionError('Network forbidden')),contextlib.redirect_stdout(io.StringIO()):
            root=pathlib.Path(tmp);config=root/'sources.json';config.write_text(json.dumps({'lookback_days':30,'max_items_per_source':12,'summary_budget':0,'sources':[source]}));data=root/'data';out=root/'output'
            collect.run(argparse.Namespace(config=config,data_dir=data,paper_export=None,source=None,no_summary=True,summary_budget=0))
            payload=json.loads((data/'index.json').read_text());self.assertEqual(payload['schema_version'],2);validate_archive(payload)
            receipt=payload['taxonomy']['classification'];self.assertEqual(receipt['quality_status'],'unmeasured');self.assertEqual(receipt['calibration_status'],'pending_human_gold')
            item=payload['items'][0];self.assertEqual(item['topic_method'],'zotero_exact');self.assertEqual(len(item['topic_labels']),1)
            build(data,out);manifest=write_manifest(out,'a'*40,'b'*40)
            self.assertEqual(manifest['archive_schema'],2);self.assertEqual(manifest['classification']['quality_status'],'unmeasured');self.assertEqual(manifest['llm_requests'],0)
            self.assertNotIn('PRIVATE_',json.dumps(payload)+json.dumps(manifest));self.assertNotIn('PRIVATE_', ''.join(p.read_text() for p in out.rglob('*.json')))
    def test_workflow_validates_build_before_remote_archive_commit_and_upload(self):
        text=(ROOT/'.github/workflows/ai4s-pages.yml').read_text()
        self.assertIn('TOPICS_MODE: v2',text);self.assertIn('ZOTERO_TOPIC_CONFIG: ${{ secrets.ZOTERO_TOPIC_CONFIG }}',text)
        self.assertLess(text.index('python site/build.py'),text.index('push origin HEAD:site-data'))
        self.assertLess(text.index('python site/deployment_manifest.py'),text.index('actions/upload-pages-artifact'))
        # GitHub sequential steps use the default success() guard; no always()
        # mutation/deploy bypass exists after a failed build.
        self.assertNotIn('if: always()',text)
if __name__=='__main__':unittest.main()
