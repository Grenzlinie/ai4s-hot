"""The public directory must cover configured collectors and remain usable without JS."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit
from lxml import html

SITE=Path(__file__).resolve().parents[1]

class SourceDirectoryTests(unittest.TestCase):
    def setUp(self):
        page = html.fromstring((SITE / 'static/sources.html').read_text())
        self.cards = page.xpath('//article[@data-source-id]')

    def test_catalog_covers_configured_sources_and_journals(self):
        entries = {card.get('data-source-id'): card for card in self.cards}
        self.assertEqual(len(entries), len(self.cards))
        sources=json.loads((SITE/'sources.json').read_text())['sources']
        journals=json.loads((SITE/'journals.json').read_text())['journals']
        self.assertEqual(set(entries),{s['id'] for s in sources}|{'journal-'+j['id'] for j in journals})
        for journal in journals:
            card = entries['journal-' + journal['id']]
            self.assertIn(journal['rss'], card.xpath('.//a/@href'))
            for issn in journal['issns']:
                self.assertIn(issn, card.text_content())
        self.assertIn('https://www.alphaxiv.org/', entries['alphaxiv'].xpath('.//a/@href'))
        self.assertEqual({j['id'] for j in journals if j['id'].startswith('nature-')},
                         {'nature-materials','nature-communications','nature-machine-intelligence','nature-computational-science'})

    def test_official_links_are_in_static_html_without_scripts(self):
        for card in self.cards:
            links=card.xpath('.//a/@href')
            self.assertTrue(any(link.startswith('./?') for link in links))
            official = urlsplit(card.xpath('.//a[@class="source-open"]/@href')[0])
            self.assertEqual(official.scheme, 'https')
            self.assertFalse(official.hostname.startswith('api.'))
            for link in card.xpath('.//a[@target="_blank"]'):
                self.assertIn('noopener',link.get('rel','').split())
        self.assertTrue((SITE/'static/sources.css').is_file())
        self.assertTrue((SITE/'static/sources.js').is_file())

if __name__=='__main__':unittest.main()
