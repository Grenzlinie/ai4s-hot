"""Offline acceptance: no credentials, network, SMTP or paid models required."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

SITE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('ai4s_' + name, SITE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect, exporter, builder = load('collect'), load('export_daily'), load('build')
SOURCE = {'id': 'one', 'name': 'One', 'kind': 'mock', 'group': 'papers', 'type': 'paper'}


class OfflineAcceptance(unittest.TestCase):
    def test_arxiv_identity_across_version_pdf_and_alphaxiv(self):
        urls = ['http://arxiv.org/abs/2609.12345v2', 'https://arxiv.org/pdf/2609.12345v1.pdf', 'https://alphaxiv.org/abs/2609.12345']
        self.assertEqual({collect.canonical_url(u) for u in urls}, {'https://arxiv.org/abs/2609.12345'})
        self.assertEqual(collect.canonical_url('https://example.com/a/?utm_source=x&q=y#top'), 'https://example.com/a?q=y')

    def test_reject_unsafe_url(self):
        with self.assertRaises(ValueError):
            collect.item(SOURCE, 'bad', 'javascript:alert(1)')

    def test_merge_idempotence_preserves_first_seen_and_signals(self):
        a = collect.item(SOURCE, 'Paper', 'https://arxiv.org/abs/2609.12345', excerpt='abstract', zotero_score=0.3)
        a['first_seen'] = '2026-09-01T00:00:00+00:00'
        b = collect.item({**SOURCE, 'id': 'alpha', 'name': 'alpha'}, 'Paper', 'https://alphaxiv.org/abs/2609.12345v2', alpha_rank=4)
        state = {a['id']: a}
        collect.merge(state, [b, b])
        self.assertEqual(len(state), 1)
        self.assertEqual(a['first_seen'], '2026-09-01T00:00:00+00:00')
        self.assertEqual(a['source_ids'], ['one', 'alpha'])
        self.assertEqual((a['zotero_score'], a['alpha_rank']), (0.3, 4))

    def test_public_export_drops_private_fields_and_nan(self):
        p = SimpleNamespace(source='arxiv', title='Paper', authors=['A'], abstract='public abstract', url='https://arxiv.org/abs/2609.12345', tldr='summary', score=float('nan'), full_text='PRIVATE_FULL_TEXT', zotero_key='PRIVATE_ZOTERO_KEY', collection='PRIVATE_COLLECTION')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'papers.json'
            exporter.export([p], path)
            payload = json.loads(path.read_text())
        text = json.dumps(payload)
        self.assertNotIn('PRIVATE', text)
        self.assertIsNone(payload['papers'][0]['zotero_score'])
        self.assertEqual(set(payload['papers'][0]), {'source', 'title', 'url', 'authors', 'abstract', 'summary', 'pdf_url', 'affiliations', 'zotero_score'})

    def setup_run(self, tmp, sources, previous=None):
        root = Path(tmp)
        config = root / 'config.json'
        config.write_text(json.dumps({'lookback_days':30, 'max_items_per_source':12, 'summary_budget':24, 'sources':sources}))
        data = root / 'data'
        if previous:
            data.mkdir()
            (data / 'index.json').write_text(json.dumps(previous))
        return argparse.Namespace(config=str(config), data_dir=str(data), paper_export=None, source=None, no_summary=True, summary_budget=None)

    def test_partial_source_failure_retains_archive_and_success_time(self):
        old = collect.item(SOURCE, 'Old', 'https://example.com/old')
        last = '2026-10-01T00:00:00+00:00'
        previous = {'items':[old], 'sources':[{'id':'one', 'last_success':last}]}
        def fetch(s, limit, cutoff):
            if s['id'] == 'one':
                raise RuntimeError('PRIVATE_CREDENTIAL_IN_EXCEPTION')
            return [collect.item(s, 'New', 'https://example.com/new')]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(collect.COLLECTORS, {'mock':fetch}), patch.object(collect.requests, 'get', side_effect=AssertionError('Network forbidden')):
            args = self.setup_run(tmp, [SOURCE, {**SOURCE, 'id':'two'}], previous)
            collect.run(args)
            payload = json.loads((Path(args.data_dir) / 'index.json').read_text())
            self.assertEqual(len(payload['items']), 2)
            status = next(s for s in payload['sources'] if s['id']=='one')
            self.assertEqual(status['last_success'], last)
            self.assertEqual(status['status'], 'error')
            self.assertNotIn('PRIVATE', json.dumps(payload))

    def test_total_outage_does_not_replace_archive(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(collect.COLLECTORS, {'mock': lambda *a: (_ for _ in ()).throw(RuntimeError('down'))}):
            args = self.setup_run(tmp, [SOURCE], {'items':[], 'sources':[]})
            index = Path(args.data_dir) / 'index.json'
            before = index.read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'All collectors failed'):
                collect.run(args)
            self.assertEqual(index.read_bytes(), before)
            self.assertFalse((Path(args.data_dir) / 'daily').exists())

    def test_archive_day_is_shanghai_even_before_utc_midnight(self):
        now = datetime(2026,10,8,23,30,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp, patch.object(collect, 'NOW', now), patch.dict(collect.COLLECTORS, {'mock':lambda s,*a:[collect.item(s,'Paper','https://example.com/day')]}):
            args = self.setup_run(tmp, [SOURCE])
            collect.run(args)
            day = Path(args.data_dir) / 'daily' / '2026-10-09.json'
            self.assertTrue(day.exists())
            self.assertEqual(len(json.loads(day.read_text())['item_ids']),1)

    def test_two_runs_do_not_duplicate_daily_items(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(collect.COLLECTORS, {'mock':lambda s,*a:[collect.item(s,'Paper','https://example.com/day')]}):
            args = self.setup_run(tmp, [SOURCE])
            collect.run(args)
            collect.run(args)
            index = json.loads((Path(args.data_dir) / 'index.json').read_text())
            self.assertEqual(len(index['items']),1)
            daily = list((Path(args.data_dir) / 'daily').glob('*.json'))
            self.assertEqual(len(json.loads(daily[0].read_text())['item_ids']),1)

    def test_build_copies_archive_and_project_relative_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'data'
            collect.write_json(data / 'index.json', {'schema_version':1,'items':[]})
            collect.write_json(data / 'daily' / '2026-10-09.json', {'item_ids':[]})
            out = root / 'zotero-arxiv-daily'
            builder.build(data,out)
            self.assertTrue((out / '.nojekyll').exists())
            self.assertTrue((out / 'data' / 'daily' / '2026-10-09.json').exists())
            text = (out / 'index.html').read_text()
            for asset in ('./style.css','./app.js','./favicon.svg'):
                self.assertIn(asset,text)
            self.assertIn("fetch('./data/index.json'", (out / 'app.js').read_text())

    def test_export_adapter_executes_ranking_and_never_smtp(self):
        calls = []
        paper = SimpleNamespace(source='arxiv', title='P', url='https://arxiv.org/abs/2609.12345', authors=[],abstract='a',tldr='',score=1,generate_tldr=lambda *a:calls.append('tldr'),generate_affiliations=lambda *a:calls.append('affiliations'))
        class FakeExecutor:
            def __init__(self):
                self.config = SimpleNamespace(executor=SimpleNamespace(max_paper_num=1),llm={})
                self.openai_client = object()
                self.retrievers = {'arxiv':SimpleNamespace(retrieve_papers=lambda:[paper,paper])}
                self.reranker = SimpleNamespace(rerank=lambda *a: calls.append('rank') or a[0])
            def fetch_zotero_corpus(self): return ['PRIVATE_CORPUS']
            def filter_corpus(self, value): return value
            def run(self): raise AssertionError('Upstream email run must never execute')
        package = ModuleType('zotero_arxiv_daily')
        ex = ModuleType('zotero_arxiv_daily.executor')
        ex.Executor = FakeExecutor
        ex.logger = SimpleNamespace(info=lambda *a:None)
        package.executor = ex
        main = ModuleType('zotero_arxiv_daily.main')
        main.main = lambda:FakeExecutor().run()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {'zotero_arxiv_daily':package,'zotero_arxiv_daily.executor':ex,'zotero_arxiv_daily.main':main}), patch.dict(exporter.os.environ, {'AI4S_PAPER_EXPORT':str(Path(tmp)/'papers.json')}), patch.object(sys,'path',list(sys.path)):
            exporter.main()
            data = json.loads((Path(tmp)/'papers.json').read_text())
            self.assertEqual(len(data['papers']),1)
        self.assertEqual(calls,['rank','tldr','affiliations'])

    def test_source_config_includes_hf_daily_and_excludes_dp(self):
        sources = json.loads((SITE / 'sources.json').read_text())['sources']
        self.assertTrue(any(s['kind']=='hf_daily' for s in sources))
        self.assertFalse(any('dp.tech' in s.get('url','') or '深势' in s['name'] for s in sources))

    def test_semantic_bounds_query_and_filters_future_publication(self):
        now = datetime(2026,10,9,8,0,tzinfo=timezone.utc)
        cutoff = datetime(2026,9,9,8,0,tzinfo=timezone.utc)
        source = next(s for s in json.loads((SITE / 'sources.json').read_text())['sources'] if s['id']=='semantic-scholar')
        def paper(title, date, arxiv=None):
            return {'title':title,'publicationDate':date,'url':'https://www.semanticscholar.org/paper/'+title,'abstract':'ML potentials','externalIds':{'ArXiv':arxiv} if arxiv else {},'authors':[{'name':'A'}]}
        response = SimpleNamespace(json=lambda:{'data':[
            paper('FutureIssue','2027-01-01'),
            paper('FutureTomorrow','2026-10-10'),
            paper('Today','2026-10-09','2610.12345'),
            paper('Valid','2026-09-25'),
        ]})
        with patch.object(collect,'NOW',now), patch.object(collect,'get',return_value=response) as get:
            result = collect.semantic(source,12,cutoff)
        params = get.call_args.kwargs['params']
        self.assertEqual(params['publicationDateOrYear'],'2026-09-09:2026-10-09')
        self.assertEqual(params['query'],source['query'])
        self.assertIn('"machine learning potentials"',params['query'])
        self.assertEqual([p['title'] for p in result],['Today','Valid'])
        self.assertEqual(result[0]['url'],'https://arxiv.org/abs/2610.12345')
        self.assertEqual(result[1]['authors'],['A'])

    def test_duplicate_channel_is_independent_of_source_completion_order(self):
        a = collect.item({**SOURCE,'group':'science'},'P','https://arxiv.org/abs/2609.12345')
        b = collect.item({**SOURCE,'id':'alpha','group':'papers'},'P','https://arxiv.org/abs/2609.12345')
        left,right = {},{}
        collect.merge(left,copy.deepcopy([a,b]))
        collect.merge(right,copy.deepcopy([b,a]))
        self.assertEqual(left[a['id']]['group'],right[a['id']]['group'])
        self.assertEqual(set(left[a['id']]['groups']),{'science','papers'})
        self.assertEqual(set(right[a['id']]['groups']),{'science','papers'})

    def test_summary_outage_is_bounded_and_secret_safe(self):
        entries = [collect.item(SOURCE, 'P', f'https://example.com/{n}', excerpt='abstract') for n in range(8)]
        with patch.dict(collect.os.environ, {'OPENAI_API_KEY':'PRIVATE_KEY','OPENAI_API_BASE':'https://private.example/v1','CUSTOM_CONFIG':'llm:\n  generation_kwargs:\n    model: mock\n'}), patch.object(collect.requests,'post',side_effect=collect.requests.RequestException('PRIVATE_KEY')) as post:
            result = collect.summarize(entries,8)
        self.assertEqual(post.call_count,3)
        self.assertEqual(result['generated'],0)
        self.assertEqual(result['status'],'partial')
        self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertTrue(all(not p['summary'] and p['excerpt']=='abstract' for p in entries))

    def test_prepare_config_removes_smtp_but_preserves_model_config(self):
        import os
        import runpy
        import yaml
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'CUSTOM_CONFIG':'email:\n  sender_password: PRIVATE_SMTP\nllm:\n  generation_kwargs:\n    model: mock\n'}):
            Path(tmp,'config').mkdir()
            original = Path.cwd()
            try:
                os.chdir(tmp)
                runpy.run_path(str(SITE / 'prepare_config.py'))
            finally:
                os.chdir(original)
            config = yaml.safe_load(Path(tmp,'config/custom.yaml').read_text())
            self.assertNotIn('email',config)
            self.assertEqual(config['llm']['generation_kwargs']['model'],'mock')


if __name__ == '__main__':
    unittest.main()
