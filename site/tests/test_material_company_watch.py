from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect import accepts_update, publication_cards, rss
from topics_decision import content_facets


class MaterialsCompanyTests(unittest.TestCase):
    def test_financing_and_generic_products_stay_out_of_technical_sources(self):
        source = {"materials_only": True}
        self.assertFalse(accepts_update(source, "Launching the Materials Foundry and a $450M Series B", "AI materials"))
        self.assertFalse(accepts_update(source, "开物纪完成天使轮融资", "训练材料模型"))
        self.assertFalse(accepts_update(source, "New generalized workbench", "A faster chat interface."))
        self.assertTrue(accepts_update(source, "Nature Is Our Learning Environment", "Interpret lab XRD data."))
        self.assertTrue(accepts_update({}, "New generalized workbench", "A faster chat interface."))

    def test_rss_prefers_official_technical_categories(self):
        feed = b"""<rss version="2.0"><channel><title>Company</title>
          <item><title>Atomistic materials dataset</title>
            <link>https://example.org/dataset</link><category>Research</category></item>
          <item><title>Materials training seminars</title>
            <link>https://example.org/events</link><category>Press</category></item>
        </channel></rss>"""
        source = {"id": "company", "name": "Company", "kind": "rss",
                  "url": "https://example.org/feed", "type": "report", "group": "science",
                  "materials_only": True, "feed_categories": ["Research"]}
        with patch("collect.get", return_value=SimpleNamespace(content=feed)):
            rows = rss(source, 12, datetime(2026, 8, 1, tzinfo=timezone.utc))
        self.assertEqual([row["title"] for row in rows], ["Atomistic materials dataset"])

    def test_research_cards_use_the_publisher_date_and_do_not_download_pdfs(self):
        page = """<main><section id="research">
            <a href="/papers/creator.pdf"><h3>Creator</h3>
              <p>面向晶体结构的材料生成模型。</p><time datetime="2026-09-24"></time></a>
            <a href="/papers/older.pdf"><h3>旧材料报告</h3>
              <time datetime="2026-07-01"></time></a>
            </section><section><a href="/news/funding/">新一轮融资</a></section></main>"""
        source = {"id": "kairos-materials", "name": "开物纪", "url": "https://example.org/news/",
                  "type": "report", "group": "science", "materials_only": True,
                  "card_xpath": "//*[@id='research']//a", "title_xpath": "string(.//h3)",
                  "excerpt_xpath": "string(.//p)"}
        with patch("collect.get", return_value=SimpleNamespace(content=page, url=source["url"])) as get:
            rows = publication_cards(source, 12, datetime(2026, 8, 1, tzinfo=timezone.utc))
        get.assert_called_once_with(source["url"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://example.org/papers/creator.pdf")
        self.assertTrue(rows[0]["published_at"].startswith("2026-09-24"))
        self.assertEqual(content_facets(rows[0]), ("research", "web:technical_report", ["web:materials"]))
