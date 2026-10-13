"""Journal adapters: metadata/date/identity/cost boundaries, no network calls."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import journals as j

NOW = datetime(2026, 10, 13, 6, tzinfo=timezone.utc)
JOURNAL = {"id": "nature-materials", "title": "Nature Materials", "publisher": "Springer Nature",
           "issns": ["1476-1122", "1476-4660"], "rss": "https://www.nature.com/nmat.rss"}


def crossref(i=1, **kw):
    return {"DOI": f"10.1234/test{i}", "title": ["Machine learning predicts alloy properties"],
            "abstract": "Machine learning predicts the mechanical properties of alloys. " * 3,
            "type": "journal-article", "published-online": {"date-parts": [[2026, 10, 12]]},
            "published-print": {"date-parts": [[2026, 12, 1]]},
            "indexed": {"date-time": "2026-10-13T01:00:00Z"}, **kw}


def rss(entries):
    return Mock(entries=entries, bozo=False)


def entry(i=1, **kw):
    return {"title": "Machine learning predicts alloy properties", "link": f"https://doi.org/10.1234/test{i}",
            "published": "2026-10-12", "summary": "Machine learning predicts alloy properties.", **kw}


class JournalTests(unittest.TestCase):
    def test_registry_ten_real_journals(self):
        rows, cfg = j._load_config(Path(j.__file__).with_suffix('.json'))
        self.assertEqual(len(rows), 10)
        self.assertIn("Advanced Functional Materials", [r["title"] for r in rows])
        self.assertEqual(cfg["workers"], 4)
        self.assertEqual(cfg["crossref_max_pages"] * cfg["crossref_rows"], 2000)

    def test_rule_ai_for_materials(self):
        for title in ["Machine learning predicts alloy properties", "AI-guided synthesis of perovskites",
                      "Foundation models for materials discovery", "Universal neural potentials for crystal simulation"]:
            with self.subTest(title=title):
                self.assertEqual(j.relevance(title)["status"], "relevant")

    def test_rule_hardware_is_not_ai_for_materials(self):
        for title in ["Memristive neural networks for artificial intelligence", "Nitrospinics: From Memory to Artificial Intelligence",
                      "Neuromorphic polymers for brain-inspired computing"]:
            with self.subTest(title=title):
                self.assertEqual(j.relevance(title)["reason"], "materials_for_ai_hardware")
        self.assertEqual(j.relevance("Memristive devices", "Machine-learning-guided synthesis for materials discovery. " * 3)["status"], "relevant")

    def test_missing_abstract_pending_not_excluded(self):
        self.assertEqual(j.relevance("Molecular weaving goes multilevel")["status"], "pending")
        self.assertEqual(j.relevance("Molecular weaving", "We weave polymers with new chemistry. " * 6)["status"], "excluded")
        self.assertEqual(j.relevance("AI for science", "A language model solves mathematics problems. " * 6)["reason"], "no_materials_research_evidence")
        self.assertEqual(j.relevance("Machine learning materials")["status"], "pending")

    def test_news_and_corrections_excluded_even_if_related(self):
        title = "Machine learning predicts alloy properties"
        self.assertEqual(j.relevance(title, doi="10.1038/d41586-026-12345")["status"], "excluded")
        self.assertEqual(j.relevance(title, article_type="News")["status"], "excluded")
        self.assertEqual(j.relevance("Correction: " + title)["status"], "excluded")

    def test_word_boundaries_ai_not_inside_words(self):
        self.assertEqual(j.relevance("Maintaining alloy strength", "Maintaining metallic materials. " * 6)["status"], "excluded")

    def test_metadata_excerpt_not_negative_evidence(self):
        for abstract in ['Advanced Materials, EarlyView.', 'Science Advances. DOI: 10.1126/sciadv.abc123',
                         'Publication date: Available online 12 October 2026 Source: Acta Materialia Author(s): ' + 'A researcher, ' * 20]:
            self.assertEqual(j.relevance('Molecular weaving goes multilevel', abstract)['status'], 'pending')
        self.assertEqual(j.relevance('Alloy modelling', 'Traditional interatomic potentials simulate metallic materials. ' * 4)['status'], 'excluded')
        self.assertEqual(j.relevance('Machine learning predicts alloy properties', article_type='Perspective')['status'], 'relevant')

    def test_sciencedirect_date_not_guessed_from_pii(self):
        row = j._rss_record(entry(link='https://www.sciencedirect.com/science/article/pii/S1359645426000012', published=None,
                                 summary='Publication date: Available online 12 October 2026 Source: Acta Materialia Author(s): Smith'))
        self.assertIsNone(row['doi'])
        self.assertTrue(row['rss_published_at'].startswith('2026-10-12'))
        self.assertIsNone(j.description_date('Publication date: October 2026 Source: Matter'))

    def test_exact_title_join_preserves_first_seen_and_no_false_merge(self):
        raw = entry(link='https://www.sciencedirect.com/science/article/pii/S1359645426000012')
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([raw])), patch.object(j, '_crossref', return_value=([], [])):
            rows, _, old = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        original_seen = rows[0]['first_seen']
        newer = NOW.replace(day=14)
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([raw])), patch.object(j, '_crossref', return_value=([j._crossref_record(crossref())], [])):
            rows, _, state = j._journal(JOURNAL, old, j.DEFAULTS, newer)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['doi'], '10.1234/test1')
        self.assertEqual(rows[0]['first_seen'], original_seen)
        self.assertNotIn(raw['link'], state['records'])

    def test_biomedical_ai_not_materials_and_function_ai_not_design(self):
        rows = [
            ('Machine learning design of RNA', 'Deep learning predicts molecular RNA structures and protein interactions. ' * 3),
            ('Drug molecule discovery', 'Machine learning discovers molecules for drug development and clinical trials. ' * 3),
            ('Plant Rubisco engineering', 'Machine learning predicts catalytic efficiencies of proteins and enzyme variants. ' * 3),
        ]
        for title, abstract in rows:
            with self.subTest(title=title):
                self.assertEqual(j.relevance(title, abstract)['status'], 'excluded')
        text = 'We design polymer sensors for wearable pressure detection. Neural networks classify gait patterns from the resulting sensor signals. '
        self.assertNotEqual(j.relevance('Wearable polymer pressure sensors', text)['status'], 'relevant')
        self.assertEqual(j.relevance('AI-guided hydrogel synthesis for drug delivery')['status'], 'relevant')

    def test_future_print_date_not_used_as_online_date(self):
        row = j._crossref_record(crossref(**{'published-online':None}))
        row['first_seen']=NOW.isoformat();row['journal_relevance']=j.relevance(row['title'],row['abstract'])
        output=j._public_item(row, JOURNAL, NOW)
        self.assertIsNone(output['published_at'])
        self.assertTrue(output['published_print_at'].startswith('2026-12-01'))

    def test_collect_doi_arrives_later_keeps_saved_identity(self):
        pii = 'https://www.sciencedirect.com/science/article/pii/S1359645426000012'
        raw = entry(link=pii)
        with tempfile.TemporaryDirectory() as directory:
            cfg, path = Path(directory)/'j.json', Path(directory)/'state.json'
            cfg.write_text(json.dumps({'journals': [JOURNAL]}))
            with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([raw])), patch.object(j, '_crossref', return_value=([], [])):
                first, _, _, state = j.collect(cfg, path, NOW)
            path.write_text(json.dumps(state))
            with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([raw])), patch.object(j, '_crossref', return_value=([j._crossref_record(crossref())], [])):
                second, _, _, state = j.collect(cfg, path, NOW.replace(day=14))
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0]['id'], second[0]['id'])
        self.assertEqual(first[0]['first_seen'], second[0]['first_seen'])
        self.assertEqual(second[0]['url'], 'https://doi.org/10.1234/test1')
        self.assertEqual(state['journals'][JOURNAL['id']]['records']['10.1234/test1']['item_id'], first[0]['id'])

    def test_ambiguous_same_title_different_dois_not_joined(self):
        pii = 'https://www.sciencedirect.com/science/article/pii/S1359645426000012'
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry(link=pii)])), patch.object(j, '_crossref', return_value=([j._crossref_record(crossref(1)), j._crossref_record(crossref(2))], [])):
            rows, _, state = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        self.assertEqual(len(rows), 3)
        self.assertIn(pii, state['records'])
        self.assertIsNone(state['records'][pii]['doi'])
        self.assertEqual(len({row['id'] for row in rows}), 3)

    def test_late_doi_after_rss_item_disappears_preserves_identity(self):
        pii = 'https://www.sciencedirect.com/science/article/pii/S1359645426000012'
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry(link=pii)])), patch.object(j, '_crossref', return_value=([], [])):
            first, _, state = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([])), patch.object(j, '_crossref', return_value=([j._crossref_record(crossref())], [])):
            second, _, state = j._journal(JOURNAL, state, j.DEFAULTS, NOW.replace(day=14))
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]['id'], first[0]['id'])
        self.assertEqual(second[0]['first_seen'], first[0]['first_seen'])
        self.assertEqual(second[0]['doi'], '10.1234/test1')
        self.assertNotIn(pii, state['records'])

    def test_late_ambiguous_doi_does_not_upgrade_cached_pii(self):
        pii = 'https://www.sciencedirect.com/science/article/pii/S1359645426000012'
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry(link=pii)])), patch.object(j, '_crossref', return_value=([], [])):
            first, _, state = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([])), patch.object(j, '_crossref', return_value=([j._crossref_record(crossref(1)), j._crossref_record(crossref(2))], [])):
            second, _, state = j._journal(JOURNAL, state, j.DEFAULTS, NOW.replace(day=14))
        self.assertEqual(len(second), 3)
        self.assertEqual(state['records'][pii]['item_id'], first[0]['id'])
        self.assertIsNone(state['records'][pii]['doi'])

    def test_doi_normalization(self):
        self.assertEqual(j.normalize_doi("https://doi.org/10.1234/ABC%2FDEF"), "10.1234/abc/def")
        self.assertIsNone(j.normalize_doi("not-a-doi"))

    def test_dates_separate_and_missing_not_invented(self):
        row = j._crossref_record(crossref())
        self.assertTrue(row["published_online_at"].startswith("2026-10-12"))
        self.assertTrue(row["published_print_at"].startswith("2026-12-01"))
        self.assertTrue(row["indexed_at"].startswith("2026-10-13"))
        self.assertIsNone(j.date_iso({"date-parts": [[2026, 12]]}))
        self.assertIsNone(j.date_iso("invalid"))
        self.assertIsNone(j._rss_record(entry())["published_online_at"])

    def test_crossref_bounded_pagination_partial(self):
        settings = {**j.DEFAULTS, "crossref_rows": 1, "crossref_max_pages": 2}
        payloads = [json.dumps({"message": {"items": [crossref(i)], "next-cursor": str(i)}}).encode() for i in (1, 2)]
        with patch.object(j, '_get', side_effect=payloads) as get:
            rows, errors = j._crossref(JOURNAL, NOW.isoformat(), settings)
        self.assertEqual(len(rows), 2)
        self.assertIn("crossref_page_cap_reached", errors)
        self.assertEqual(get.call_count, 2)
        self.assertIn('from-index-date:2026-10-13', get.call_args.kwargs.get('params', get.call_args.args[1])["filter"])

    def test_crossref_page_failure_retains_earlier_batch(self):
        payload = json.dumps({"message": {"items": [crossref()], "next-cursor": "next"}}).encode()
        with patch.object(j, '_get', side_effect=[payload, RuntimeError('PRIVATE_ERROR')]):
            rows, errors = j._crossref(JOURNAL, NOW.isoformat(), {**j.DEFAULTS, "crossref_rows": 1})
        self.assertEqual(len(rows), 1)
        self.assertEqual(errors, ["crossref_request_or_parse_failed"])

    def test_rss_entire_feed_not_twelve_and_merge_doi(self):
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry(i) for i in range(30)])), patch.object(j, '_crossref', return_value=([j._crossref_record(crossref(1))], [])):
            rows, health, state = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        self.assertEqual(len(rows), 30)
        self.assertEqual(len(state["records"]), 30)
        self.assertEqual(health['status'], 'ok')
        self.assertEqual(state['records']['10.1234/test1']['providers'], ['crossref', 'rss'])
        self.assertEqual(rows[1]['source_ids'], ['journal-nature-materials'])

    def test_outage_retains_previous_and_first_seen(self):
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry()])), patch.object(j, '_crossref', return_value=([], [])):
            rows, _, old = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        with patch.object(j, '_get', side_effect=RuntimeError('PRIVATE')), patch.object(j, '_crossref', return_value=([], ['crossref_request_or_parse_failed'])):
            retained, health, state = j._journal(JOURNAL, old, j.DEFAULTS, NOW)
        self.assertEqual(retained, rows)
        self.assertEqual(health['status'], 'error')
        self.assertEqual(state['last_success_at'], old['last_success_at'])
        self.assertNotIn('PRIVATE', json.dumps(health))

    def test_pending_can_become_excluded_state_available(self):
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry(title='Molecular weaving', summary='')])), patch.object(j, '_crossref', return_value=([], [])):
            rows, _, old = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        self.assertEqual(rows[0]['journal_relevance']['status'], 'pending')
        new = j._crossref_record(crossref(title=['Molecular weaving'], abstract='We weave polymers with new chemistry. ' * 6))
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([])), patch.object(j, '_crossref', return_value=([new], [])):
            rows, _, state = j._journal(JOURNAL, old, j.DEFAULTS, NOW)
        self.assertEqual(rows, [])
        self.assertEqual(state['records']['10.1234/test1']['journal_relevance']['status'], 'excluded')
        self.assertEqual(state['records']['10.1234/test1']['first_seen'], old['records']['10.1234/test1']['first_seen'])

    def test_undated_unseen_rss_not_published_as_new(self):
        with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([entry(published=None)])), patch.object(j, '_crossref', return_value=([], [])):
            rows, _, _ = j._journal(JOURNAL, {}, j.DEFAULTS, NOW)
        self.assertEqual(rows, [])

    def test_initial_window_and_recovery_overlap(self):
        for previous, expected in [({}, '2026-09-29'), ({'last_crossref_at': '2026-10-12T06:00:00+00:00'}, '2026-10-09')]:
            with patch.object(j, '_get', return_value=b'RSS'), patch.object(j.feedparser, 'parse', return_value=rss([])), patch.object(j, '_crossref', return_value=([], [])) as fetch:
                j._journal(JOURNAL, previous, j.DEFAULTS, NOW)
            self.assertTrue(fetch.call_args.args[1].startswith(expected))

    def test_collect_unwritten_state_and_journal_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg, statepath = Path(directory)/'journals.json', Path(directory)/'state.json'
            cfg.write_text(json.dumps({'journals': [JOURNAL, {**JOURNAL, 'id':'other'}]}))
            with patch.object(j, '_journal', side_effect=[ValueError('PRIVATE'), ([], {'id':'journal-other', 'status':'ok'}, {'records':{}})]):
                rows, statuses, registry, state = j.collect(cfg, statepath, NOW)
            self.assertEqual([s['status'] for s in statuses], ['error', 'ok'])
            self.assertEqual(len(registry), 2)
            self.assertFalse(statepath.exists())
            self.assertNotIn('PRIVATE', json.dumps(state))

    def test_invalid_budgets_and_duplicate_id_fail(self):
        for change in [{'workers':5}, {'crossref_max_pages':11}, {'crossref_rows':201}, {'enabled':'yes'}, {'journals':[JOURNAL,JOURNAL]}]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'j.json'
                path.write_text(json.dumps({'journals':[JOURNAL], **change}))
                with self.assertRaises(ValueError): j._load_config(path)

    def test_response_size_and_timeout_retries_bounded(self):
        r = Mock(); r.__enter__ = Mock(return_value=r); r.__exit__ = Mock(return_value=False)
        r.iter_content.return_value = [b'x'*5_000_001]
        with patch.object(j.requests, 'get', return_value=r) as get, patch.object(j.time, 'sleep'):
            with self.assertRaises(RuntimeError): j._get('https://example.org')
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.kwargs['timeout'], (5,20))

if __name__ == '__main__':
    unittest.main()
