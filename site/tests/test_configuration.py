"""Configuration safety tests use synthetic files and never contact GitHub."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('configure', ROOT / 'scripts/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)
MODEL = 'deepseek/deepseek-v4.1-flash'
ENV = 'OPENAI_API_KEY="SYNTHETIC_PRIVATE=a=b"\nOPENAI_API_BASE=https://example.test/v1\nZOTERO_ID=123\nZOTERO_KEY=\'SYNTHETIC_ZOTERO==\'\nALPHAXIV_API_KEY=SYNTHETIC_ALPHA\n'
CONFIG = 'llm:\n  generation_kwargs:\n    model: ' + MODEL + '\n'


class ConfigurationAcceptance(unittest.TestCase):
    def files(self, tmp, env=ENV, config=CONFIG):
        env_path, config_path = Path(tmp)/'synthetic.env', Path(tmp)/'synthetic.yaml'
        env_path.write_text(env)
        config_path.write_text(config)
        return env_path, config_path

    def test_quotes_and_equal_signs_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            env, _ = self.files(tmp)
            parsed = configure.read_credentials(env)
        self.assertEqual(parsed['OPENAI_API_KEY'], 'SYNTHETIC_PRIVATE=a=b')
        self.assertEqual(parsed['ZOTERO_KEY'], 'SYNTHETIC_ZOTERO==')

    def test_api_endpoint_normalizes_to_root_without_changing_valid_root(self):
        root = 'https://openrouter.ai/api/v1'
        for base in (root, root+'/', root+'/chat/completions', root+'/chat/completions/'):
            with self.subTest(base=base), tempfile.TemporaryDirectory() as tmp:
                env, _ = self.files(tmp, ENV.replace('https://example.test/v1',base))
                self.assertEqual(configure.read_credentials(env)['OPENAI_API_BASE'],root)

    def test_model_preserved_smtp_removed_inline_credentials_replaced(self):
        config = CONFIG + '  api:\n    key: SYNTHETIC_PRIVATE\n    base_url: https://inline.example/v1\nzotero:\n  api_key: SYNTHETIC_ZOTERO\n  user_id: 456\nemail:\n  sender_password: SYNTHETIC_SMTP\n'
        with tempfile.TemporaryDirectory() as tmp:
            _, path = self.files(tmp, config=config)
            public, model = configure.read_config(path)
        self.assertEqual(model, MODEL)
        self.assertNotIn('SYNTHETIC', public)
        result = yaml.safe_load(public)
        self.assertNotIn('email', result)
        self.assertEqual(result['llm']['api']['key'], '${oc.env:OPENAI_API_KEY}')
        self.assertEqual(result['zotero']['api_key'], '${oc.env:ZOTERO_KEY}')

    def test_invalid_inputs_never_write(self):
        cases = [
            ('OPENAI_API_KEY=x\n', CONFIG),
            (ENV, 'llm: [broken'),
            (ENV, 'llm: null'),
            (ENV, 'llm: {generation_kwargs: null}'),
            (ENV, CONFIG + '  api: []\n'),
            (ENV, CONFIG + 'zotero: []\n'),
            (ENV, CONFIG + 'reranker:\n  api:\n    key: SYNTHETIC_PRIVATE\n'),
        ]
        for env_content, config_content in cases:
            with self.subTest(config=config_content[:32]), tempfile.TemporaryDirectory() as tmp:
                env, config = self.files(tmp, env_content, config_content)
                with patch.object(sys, 'argv', ['configure.py','--env',str(env),'--config',str(config)]), patch.object(configure.subprocess,'run') as run:
                    with self.assertRaises((ValueError,yaml.YAMLError)):
                        configure.main()
                    run.assert_not_called()

    def test_secret_values_use_stdin_never_argv_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            env, config = self.files(tmp)
            output = io.StringIO()
            with patch.object(sys,'argv',['configure.py','--env',str(env),'--config',str(config),'--run']), patch.object(configure.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run, contextlib.redirect_stdout(output):
                configure.main()
        calls = run.call_args_list
        self.assertEqual(len(calls),9)  # 5 Secrets, 2 variables, 2 workflow dispatches.
        for call in calls:
            self.assertNotIn('SYNTHETIC', ' '.join(call.args[0]))
            self.assertTrue(call.kwargs['capture_output'])
        self.assertEqual(calls[0].kwargs['input'],'SYNTHETIC_PRIVATE=a=b')
        self.assertNotIn('SYNTHETIC', output.getvalue())
        self.assertIn(MODEL,output.getvalue())
        self.assertEqual(calls[6].kwargs['input'],'true')
        self.assertEqual(calls[-2].args[0][1:4],['workflow','run','main.yml'])

    def test_github_failure_does_not_echo_submitted_data(self):
        with patch.object(configure.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='SYNTHETIC_SECRET',stderr='SYNTHETIC_SECRET')):
            with self.assertRaises(RuntimeError) as error:
                configure.github(['secret','set','OPENAI_API_KEY'],'SYNTHETIC_SECRET')
        self.assertNotIn('SYNTHETIC',str(error.exception))

    def test_example_and_workflow_have_required_upstream_configuration(self):
        config = yaml.safe_load((ROOT/'config.example.yaml').read_text())
        self.assertEqual(config['zotero']['user_id'],'${oc.env:ZOTERO_ID}')
        self.assertEqual(config['zotero']['api_key'],'${oc.env:ZOTERO_KEY}')
        self.assertEqual(config['executor']['source'],['arxiv'])
        self.assertGreater(len(config['source']['arxiv']['category']),0)
        self.assertEqual(config['llm']['generation_kwargs']['model'],MODEL)
        workflow = yaml.load((ROOT/'.github/workflows/main.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(workflow['jobs']['calculate-and-export']['if'],"${{ vars.ZOTERO_ENABLED == 'true' }}")


if __name__=='__main__':
    unittest.main()
