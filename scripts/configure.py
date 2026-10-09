"""Sync local credentials and YAML configuration without logging their values."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import yaml

REQUIRED = ('OPENAI_API_KEY', 'OPENAI_API_BASE', 'ZOTERO_ID', 'ZOTERO_KEY')
OPTIONAL = ('ALPHAXIV_API_KEY', 'SEMANTIC_SCHOLAR_API_KEY')


def read_credentials(path):
    result = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        name, separator, value = line.partition('=')
        name, value = name.strip(), value.strip()
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', name):
            raise ValueError('Invalid credential file format; expected NAME=value')
        if name not in REQUIRED + OPTIONAL:
            raise ValueError('Unsupported credential name: ' + name)
        if name in result:
            raise ValueError('Duplicate credential name: ' + name)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '\"\'':
            value = value[1:-1]
        result[name] = value
    missing = [name for name in REQUIRED if not result.get(name)]
    if missing:
        raise ValueError('Missing credentials: ' + ', '.join(missing))
    return result


def read_config(path):
    config = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a YAML mapping')
    config.pop('email', None)
    llm = config.get('llm', {})
    if not isinstance(llm, dict) or not isinstance(llm.get('generation_kwargs', {}), dict):
        raise ValueError('llm and llm.generation_kwargs must be YAML mappings')
    model = llm.get('generation_kwargs', {}).get('model')
    if not isinstance(model, str) or not model.strip():
        raise ValueError('Set llm.generation_kwargs.model in the local YAML')
    for section, fields in (
        ('llm', {'key':'OPENAI_API_KEY', 'base_url':'OPENAI_API_BASE'}),
        ('zotero', {'user_id':'ZOTERO_ID', 'api_key':'ZOTERO_KEY'}),
    ):
        parent = config.setdefault(section, {})
        if not isinstance(parent, dict):
            raise ValueError(section + ' must be a YAML mapping')
        if section == 'llm':
            parent = parent.setdefault('api', {})
            if not isinstance(parent, dict):
                raise ValueError('llm.api must be a YAML mapping')
        for field, variable in fields.items():
            parent[field] = '${oc.env:' + variable + '}'
    # CUSTOM_CONFIG is a public repository variable. Additional API credentials
    # must also be environment references; no inline secrets are published.
    def check_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('key', 'api_key', 'password', 'sender_password') and child is not None:
                    if not isinstance(child, str) or (child and not re.fullmatch(r'\$\{oc\.env:[A-Z][A-Z0-9_]*\}', child)):
                        raise ValueError('API credentials in YAML must use environment references')
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)
    check_keys(config)
    return yaml.safe_dump(config, allow_unicode=True, sort_keys=False), model


def github(arguments, value=None):
    result = subprocess.run(['gh', *arguments], input=value, text=True, capture_output=True)
    if result.returncode:
        # Do not echo command output: a provider error could contain submitted data.
        raise RuntimeError('GitHub operation failed; check gh authentication and repository access')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='Grenzlinie/ai4s-hot')
    parser.add_argument('--env', default='.env')
    parser.add_argument('--config', default='config.local.yaml')
    parser.add_argument('--run', action='store_true', help='Run both collectors after syncing')
    args = parser.parse_args()
    credentials = read_credentials(args.env)
    config, model = read_config(args.config)
    for name, value in credentials.items():
        if value:
            github(['secret', 'set', name, '--repo', args.repo], value)
            print('Synced Secret: ' + name)
    github(['variable', 'set', 'CUSTOM_CONFIG', '--repo', args.repo], config)
    github(['variable', 'set', 'ZOTERO_ENABLED', '--repo', args.repo], 'true')
    print('Synced local YAML; model: ' + model)
    if args.run:
        github(['workflow', 'run', 'main.yml', '--repo', args.repo])
        github(['workflow', 'run', 'ai4s-pages.yml', '--repo', args.repo])
        print('Started paper ranking and site update workflows')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, yaml.YAMLError) as error:
        # YAML parser diagnostics can contain file contents, including accidental secrets.
        print(str(error) if isinstance(error, (ValueError, RuntimeError)) else 'Cannot read local configuration; check file format and path', file=sys.stderr)
        sys.exit(1)
