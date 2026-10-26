"""Bounded journal metadata collection; public records only, no model/API secrets.

collect() is side-effect free with respect to state files. The caller commits the
returned state only after its complete archive update succeeds. Records include
excluded decisions so the caller can remove a formerly pending DOI from archives.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import copy
import html
import json
from pathlib import Path
import re
import time
from urllib.parse import unquote, urlsplit

import feedparser
import requests

UTC = timezone.utc
HEADERS = {"User-Agent": "AI4S-Hot/1.0 (https://github.com/Grenzlinie/ai4s-hot)", "Accept": "application/json,application/xml,text/xml,*/*;q=0.5"}
DEFAULTS = {"enabled": True, "overlap_days": 3, "initial_days": 14, "crossref_rows": 200,
            "crossref_max_pages": 10, "retention_days": 90, "workers": 4}
# Match phrases, not substrings such as 'AI' within 'maintaining'.
AI = re.compile(r"\b(?:artificial intelligence|ai[ -](?:guided|driven|assisted)|machine[ -]learning|deep[ -]learning|neural networks?|graph neural|foundation models?|large language models?|language models?|reinforcement learning|active learning|bayesian optimi[sz]ation|generative (?:models?|ai)|self[ -]driving|autonomous (?:laborator\w*|discover\w*|experiment\w*|synth\w*)|data[ -]driven|machine[ -]learning potentials?|neural potentials?|equivariant (?:models?|networks?))\b", re.I)
MATERIAL = re.compile(r"\b(?:materials?|crystals?|alloys?|polymers?|hydrogels?|ionogels?|composites?|thermoelectric\w*|solar cells?|solar evaporators?|electrolytes?|electrodes?|batter(?:y|ies)|catalysts?|catalysis|electrocatal\w*|ceramics?|metals?|metallic|perovskites?|semiconductors?|nanomaterials?|nanoparticles?|solid[ -]state|microstructure\w*|interatomic|spintron\w*|memrist\w*|nitrospin\w*|photovoltaic\w*|thermal conductivity|mechanical properties|density functional)\b", re.I)
TASK = re.compile(r"\b(?:discover\w*|design\w*|predict\w*|screen\w*|optimi[sz]\w*|synthesi[sz]\w*|synthesis|characteri[sz]\w*|simulat\w*|potentials?|force fields?|autonomous laborator\w*|self[ -]driving laborator\w*|structure[ -]property|inverse design|property estimation|mechanism\w*)\b", re.I)
HARDWARE = re.compile(r"\b(?:neuromorphic|in[ -]memory computing|reservoir computing|artificial synapses?|memrist\w*|spintron\w*|nitrospin\w*|neural hardware|brain[ -]inspired computing|computing hardware|hardware (?:accelerat\w*|for))\b", re.I)
# An explicit computational materials task can override hardware vocabulary.
RESEARCH_TASK = re.compile(r"\b(?:machine[ -]learning[ -](?:guided|driven)|predict(?:ion|ing|s)? (?:of )?(?:material\w*|propert\w*|structure\w*|crystal\w*)|materials? (?:discover\w*|design\w*)|inverse design|interatomic potential\w*|force fields?|autonomous (?:laborator\w*|synth\w*))\b", re.I)
NON_RESEARCH = re.compile(r"\b(?:editorial|correction|retraction|obituary|news|commentary|book review|publisher correction|author correction|research highlight)\b", re.I)
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s<>\"?#]+", re.I)


def plain(value):
    return re.sub(r"[‐‑‒–—]", "-", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))))).strip()


def normalize_doi(value):
    found = DOI_PATTERN.search(unquote(str(value or "")))
    return found.group(0).rstrip(".,;)").lower() if found else None


def date_iso(value):
    if not value:
        return None
    try:
        if isinstance(value, dict):
            if value.get("date-time"):
                return date_iso(value["date-time"])
            parts = value.get("date-parts", [[]])[0]
            if len(parts) < 3:  # Do not pretend an issue year/month is a day.
                return None
            value = datetime(*parts[:3], tzinfo=UTC)
        if not isinstance(value, datetime):
            try:
                value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                value = parsedate_to_datetime(str(value))
        return value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC).isoformat()
    except (ValueError, TypeError, OverflowError, IndexError):
        return None


def title_key(value):
    return re.sub(r"[^\w]", "", plain(value).casefold())


def clean_abstract(value, title=""):
    text = plain(value)
    # Date/journal/author-only RSS descriptions are not negative AI evidence.
    if len(text) < 100 or title_key(text) == title_key(title):
        return ""
    if text.startswith("Publication date:"):
        # ScienceDirect metadata descriptions have labels followed by authors.
        if "Abstract" not in text:
            return ""
        text = text.split("Abstract", 1)[1].strip(" :")
    return text if len(text) >= 100 else ""


def description_date(value):
    text = plain(value)
    match = re.search(r"Publication date:\s*(?:Available online\s*)?(\d{1,2} [A-Za-z]+ \d{4}|[A-Za-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})", text, re.I)
    if not match:
        return None
    raw = match.group(1)
    parsed = date_iso(raw)
    if parsed:
        return parsed
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC).isoformat()
        except ValueError:
            pass
    return None


def relevance(title, abstract="", article_type="", doi=None):
    """Conservative AI-for-materials rules; unknown abstracts remain pending."""
    title, abstract = plain(title), clean_abstract(abstract, title)
    def decision(status, reason):
        return {"status": status, "method": "rule-v1", "reason": reason, "version": "1"}
    if NON_RESEARCH.search(article_type) or (doi and re.match(r"10\.1038/d41586-", doi)):
        return decision("excluded", "non_research_article")
    if re.match(r"^(?:correction|retraction|editorial|publisher correction|author correction)\b", title, re.I):
        return decision("excluded", "non_research_article")
    text = title + " " + abstract
    if re.search(r"\((?:Adv\.? Funct\.? Mater\.?|Adv\.? Energy Mater\.?|Adv\.? Mater\.?) \d+/\d{4}\)$", title, re.I):
        return decision("excluded", "journal_cover_or_issue_item")
    if HARDWARE.search(title) and not RESEARCH_TASK.search(text):
        return decision("excluded", "materials_for_ai_hardware")
    # Evidence of AI, materials and a research task must be local in the text.
    # A paper designing a sensor then using AI for gait classification does not
    # become AI-guided materials design merely because both occur somewhere.
    segments = [title] + re.split(r"(?<=[.!?])\s+", abstract)
    for segment in segments:
        if AI.search(segment) and MATERIAL.search(segment) and TASK.search(segment):
            return decision("relevant", "ai_method_for_materials_research")
    if not abstract:
        return decision("pending", "abstract_missing_or_insufficient")
    if not AI.search(text):
        return decision("excluded", "no_ai_method_evidence")
    if not MATERIAL.search(text):
        return decision("excluded", "no_materials_research_evidence")
    return decision("pending", "relationship_requires_review")


def _get(url, params=None):
    """At most two attempts and 5 MB per response; no paid endpoints."""
    last = None
    for attempt in range(2):
        try:
            with requests.get(url, params=params, headers=HEADERS, timeout=(5, 20), stream=True) as response:
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 5_000_000:
                        raise ValueError("response_size_limit")
                return bytes(data)
        except (requests.RequestException, ValueError) as error:
            last = error
            if attempt == 0:
                time.sleep(0.5)
    raise RuntimeError("metadata_request_failed") from last


def _rss_record(entry):
    title = plain(entry.get("title"))
    link = entry.get("link") or ""
    doi = normalize_doi(entry.get("prism_doi") or entry.get("dc_identifier") or entry.get("id") or link)
    if not doi:
        doi = normalize_doi(entry.get("summary"))
    if not title or not (doi or link.startswith("https://")):
        return None
    types = [entry.get("prism_section", ""), entry.get("dc_type", ""), entry.get("type", "")]
    types.extend(t.get("term", "") for t in entry.get("tags", []))
    # RSS date is retained separately: feed updates are not proven online dates.
    return {"doi": doi, "title": title, "url": "https://doi.org/" + doi if doi else link,
            "abstract": clean_abstract(entry.get("summary") or " ".join(x.get("value", "") for x in entry.get("content", [])), title),
            "rss_published_at": date_iso(entry.get("published") or entry.get("updated") or entry.get("dc_date")) or description_date(entry.get("summary", "")),
            "published_online_at": None, "published_print_at": None, "indexed_at": None,
            "article_type": " ".join(str(t) for t in types), "providers": ["rss"],
            "authors": [plain(a.get("name")) for a in entry.get("authors", []) if a.get("name")]}


def _crossref_record(row):
    doi = normalize_doi(row.get("DOI"))
    title = plain((row.get("title") or [""])[0])
    if not doi or not title:
        return None
    return {"doi": doi, "title": title, "url": "https://doi.org/" + doi,
            "abstract": clean_abstract(row.get("abstract"), title), "rss_published_at": None,
            "published_online_at": date_iso(row.get("published-online")),
            "published_print_at": date_iso(row.get("published-print")), "indexed_at": date_iso(row.get("indexed")),
            "article_type": str(row.get("subtype") or row.get("type") or ""), "providers": ["crossref"],
            "authors": [plain(" ".join([a.get("given", ""), a.get("family", "")])) for a in row.get("author", [])]}


def _key(row):
    return row.get("doi") or row["url"]


def merge_record(old, new):
    """Preserve richer abstracts and first_seen, prefer Crossref date provenance."""
    result = copy.deepcopy(old)
    for field, value in new.items():
        if field in ("first_seen", "item_id", "journal_relevance", "providers"):
            continue
        if field == "abstract":
            if len(value or "") > len(result.get(field) or ""):
                result[field] = value
        elif value is not None and value != "" and value != []:
            result[field] = value
    result["providers"] = sorted(set(old.get("providers", [])) | set(new.get("providers", [])))
    return result


def _crossref(journal, since, settings):
    rows, errors, cursor = [], [], "*"
    for page in range(settings["crossref_max_pages"]):
        params = {"filter": "type:journal-article,from-index-date:" + since[:10] + ",from-pub-date:" + settings.get("publication_cutoff", since[:10]), "rows": settings["crossref_rows"],
                  "cursor": cursor, "sort": "indexed", "order": "desc"}
        try:
            payload = json.loads(_get("https://api.crossref.org/journals/" + journal["issns"][-1] + "/works", params))
            message = payload["message"]
            batch = message["items"]
            if not isinstance(batch, list):
                raise ValueError("invalid_crossref_items")
        except (RuntimeError, ValueError, KeyError, TypeError):
            errors.append("crossref_request_or_parse_failed")
            break
        for entry in batch:
            record = _crossref_record(entry)
            if record:
                rows.append(record)
        if len(batch) < settings["crossref_rows"]:
            break
        next_cursor = message.get("next-cursor")
        if not next_cursor or next_cursor == cursor:
            errors.append("crossref_pagination_incomplete")
            break
        cursor = next_cursor
        if page == settings["crossref_max_pages"] - 1:
            errors.append("crossref_page_cap_reached")
    return rows, errors


def _public_item(row, journal, now):
    known_dates = [row.get("published_online_at"), row.get("rss_published_at"), row.get("published_print_at")]
    published = next((date for date in known_dates if date and datetime.fromisoformat(date) <= now), None)
    url = row["url"]
    return {"id": row.get("item_id") or sha256(url.encode()).hexdigest()[:24], "url": url, "title": row["title"],
            "source_ids": ["journal-" + journal["id"]], "source_names": [journal["title"]],
            "group": "science", "groups": ["science"], "type": "paper", "tags": ["materials"],
            "published_at": published, "first_seen": row["first_seen"],
            "excerpt": row.get("abstract", "")[:2200], "summary": "", "summary_kind": "source_excerpt",
            "authors": row.get("authors", []), "journal_id": journal["id"], "journal_title": journal["title"],
            "journal_issns": journal["issns"], "publisher": journal["publisher"], "doi": row.get("doi"),
            "published_online_at": row.get("published_online_at"), "published_print_at": row.get("published_print_at"),
            "indexed_at": row.get("indexed_at"), "journal_relevance": row["journal_relevance"]}


def _journal(journal, previous, settings, now):
    timestamp = now.isoformat()
    records = copy.deepcopy(previous.get("records", {}))
    initial = not previous.get("last_crossref_at")
    since = now - timedelta(days=settings["initial_days"] if initial else settings["overlap_days"])
    if previous.get("last_crossref_at"):
        # Recover missed runs, rather than permanently losing a multi-day outage.
        previous_date = date_iso(previous["last_crossref_at"])
        if previous_date:
            since = min(since, datetime.fromisoformat(previous_date) - timedelta(days=settings["overlap_days"]))
    errors, fresh = [], []
    rss_ok = False
    try:
        feed = feedparser.parse(_get(journal["rss"]))
        if not feed.entries and feed.bozo:
            raise ValueError("invalid_feed")
        # Entire feed, never the global collector's per-source 12-item limit.
        for entry in feed.entries:
            row = _rss_record(entry)
            if row:
                fresh.append(row)
        rss_ok = True
    except (RuntimeError, ValueError, TypeError):
        errors.append("rss_request_or_parse_failed")
    request_settings = {**settings, "publication_cutoff": (now - timedelta(days=settings["retention_days"])).date().isoformat()}
    crossref, crossref_errors = _crossref(journal, since.isoformat(), request_settings)
    fresh.extend(crossref)
    errors.extend(crossref_errors)
    cutoff = now - timedelta(days=settings["retention_days"])
    # Exact title joining only; no inferred DOI from PII or fuzzy matching.
    title_dois = {}
    for record in list(records.values()) + fresh:
        normalized_title = title_key(record["title"])
        if record.get("doi") and len(normalized_title) >= 24:
            title_dois.setdefault(normalized_title, set()).add(record["doi"])
    # Identical titles can belong to a correction, cover and article, or distinct
    # articles. Only unambiguous one-DOI associations can upgrade a PII record.
    doi_by_title = {title: next(iter(dois)) for title, dois in title_dois.items() if len(dois) == 1}
    # The publisher RSS may have already dropped a PII-only item by the time
    # Crossref indexes its DOI. Upgrade cached candidates as well as fresh RSS.
    for previous_key, previous_record in list(records.items()):
        matching_doi = doi_by_title.get(title_key(previous_record["title"]))
        if previous_record.get("doi") or not matching_doi:
            continue
        moved = records.pop(previous_key)
        moved.setdefault("item_id", sha256(moved["url"].encode()).hexdigest()[:24])
        moved["doi"], moved["url"] = matching_doi, "https://doi.org/" + matching_doi
        existing = records.get(matching_doi)
        if existing:
            # If both identities were already cached, retain the oldest seen ID.
            first, second = sorted((moved, existing), key=lambda r: r.get("first_seen", ""))
            records[matching_doi] = merge_record(first, second)
        else:
            records[matching_doi] = moved
    for row in fresh:
        if not row.get("doi") and title_key(row["title"]) in doi_by_title:
            old_key = _key(row)
            row["doi"] = doi_by_title[title_key(row["title"])]
            row["url"] = "https://doi.org/" + row["doi"]
            if old_key in records:
                moved = records.pop(old_key)
                moved.setdefault("item_id", sha256(moved["url"].encode()).hexdigest()[:24])
                moved["doi"], moved["url"] = row["doi"], row["url"]
                records[row["doi"]] = merge_record(records.get(row["doi"], moved), moved)
        key = _key(row)
        prior = records.get(key)
        date = row.get("published_online_at") or row.get("rss_published_at") or row.get("published_print_at")
        # Undated unseen RSS cannot become endlessly 'new' through first_seen.
        if prior is None and date is None:
            continue
        if date and datetime.fromisoformat(date) < cutoff and prior is None:
            continue
        row["first_seen"] = prior.get("first_seen", timestamp) if prior else timestamp
        records[key] = merge_record(prior, row) if prior else row
        records[key].setdefault("item_id", sha256((prior or row)["url"].encode()).hexdigest()[:24])
    for key, row in list(records.items()):
        row["journal_relevance"] = relevance(row["title"], row.get("abstract", ""), row.get("article_type", ""), row.get("doi"))
        date = row.get("published_online_at") or row.get("rss_published_at") or row.get("published_print_at")
        if date and datetime.fromisoformat(date) < cutoff:
            del records[key]
    counts = {kind: sum(r["journal_relevance"]["status"] == kind for r in records.values()) for kind in ("relevant", "pending", "excluded")}
    status = "partial" if errors and (rss_ok or crossref or not crossref_errors) else "error" if errors else "ok"
    last_success = timestamp if status == "ok" else previous.get("last_success_at")
    # 'last_success_at' is deliberately not advanced after a page cap or outage.
    state = {"last_success_at": last_success, "last_crossref_at": timestamp if not crossref_errors else previous.get("last_crossref_at"), "records": records, "counters": counts}
    public = [_public_item(row, journal, now) for row in records.values() if row["journal_relevance"]["status"] != "excluded"]
    health = {"id": "journal-" + journal["id"], "name": journal["title"], "url": journal["rss"],
              "kind": "journal", "group": "science", "type": "paper", "status": status,
              "last_attempt": timestamp, "last_success": last_success, "count": len(public),
              "counters": {**counts, "fetched": len(fresh)}, "errors": errors}
    return public, health, state


def _load_config(config_path):
    config = json.loads(Path(config_path).read_text())
    if isinstance(config, list):
        config = {"journals": config}
    settings = {**DEFAULTS, **{k: v for k, v in config.items() if k in DEFAULTS}}
    for key, minimum, maximum in [("overlap_days", 1, 14), ("initial_days", 1, 30), ("crossref_rows", 1, 200),
                                  ("crossref_max_pages", 1, 10), ("retention_days", 14, 365), ("workers", 1, 4)]:
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError("invalid_journal_setting:" + key)
    if not isinstance(settings["enabled"], bool):
        raise ValueError("invalid_journal_setting:enabled")
    journals = config.get("journals", [])
    ids = set()
    for j in journals:
        if not isinstance(j, dict) or not all(isinstance(j.get(k), str) and j[k] for k in ["id", "title", "publisher", "rss"]):
            raise ValueError("invalid_journal_registry")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", j["id"]) or j["id"] in ids:
            raise ValueError("invalid_or_duplicate_journal_id")
        ids.add(j["id"])
        if not isinstance(j.get("issns"), list) or not j["issns"] or not all(re.fullmatch(r"\d{4}-\d{3}[\dX]", i) for i in j["issns"]):
            raise ValueError("invalid_journal_issns")
        url = urlsplit(j["rss"])
        if url.scheme != "https" or not url.hostname or url.username or url.port not in (None, 443):
            raise ValueError("invalid_journal_rss_url")
    return journals, settings


def collect(config_path, state_path, now):
    """Return items, per-journal statuses, public registry, and unwritten state.

    state['journals'][id]['records'][doi_or_url]['journal_relevance']['status']
    exposes excluded decisions for removing stale pending archive entries.
    """
    now = datetime.fromisoformat(date_iso(now))
    journals, settings = _load_config(config_path)
    registry = [{k: j[k] for k in ("id", "title", "issns", "publisher")} for j in journals]
    previous = {"version": 1, "journals": {}}
    if Path(state_path).exists():
        previous = json.loads(Path(state_path).read_text())
        if previous.get("version") != 1 or not isinstance(previous.get("journals"), dict):
            raise ValueError("invalid_journal_state")
    if not settings["enabled"]:
        return [], [], registry, previous
    state = {"version": 1, "updated_at": now.isoformat(), "journals": {}}
    if "metadata_budget" in previous:
        state["metadata_budget"] = copy.deepcopy(previous["metadata_budget"])
    items, statuses = [], []
    def work(j):
        old = previous["journals"].get(j["id"], {})
        try:
            return _journal(j, old, settings, now)
        except Exception:
            # A single malformed publisher payload never deletes cached records
            # or prevents independent journals from refreshing. No raw errors.
            retained = copy.deepcopy(old)
            rows = [_public_item(r, j, now) for r in old.get("records", {}).values()
                    if r.get("journal_relevance", {}).get("status") in ("pending", "relevant")]
            return rows, {"id": "journal-" + j["id"], "name": j["title"], "url": j["rss"],
                          "kind": "journal", "group": "science", "type": "paper", "status": "error",
                          "last_attempt": now.isoformat(), "last_success": old.get("last_success_at"),
                          "count": len(rows), "errors": ["journal_adapter_failed"], "counters": {}}, retained
    with ThreadPoolExecutor(max_workers=settings["workers"]) as pool:
        for journal, result in zip(journals, pool.map(work, journals)):
            rows, health, journal_state = result
            items.extend(rows)
            statuses.append(health)
            state["journals"][journal["id"]] = journal_state
    # Public metadata recovery is opt-in for deployed configuration. Synthetic
    # source configs and callers retain the previous no-extra-request behavior.
    raw_config = json.loads(Path(config_path).read_text())
    recovery_config = raw_config if isinstance(raw_config, dict) else {}
    if recovery_config.get("metadata", {}).get("enabled", False):
        from journal_metadata import enrich_candidates
        before = {(jid, key): row.get("abstract", "") for jid, block in state["journals"].items()
                  for key, row in block.get("records", {}).items()}
        receipt = enrich_candidates(state, recovery_config, now)
        items = []
        for journal, health in zip(journals, statuses):
            records = state["journals"][journal["id"]].get("records", {})
            recovered = 0
            for key, row in records.items():
                if row.get("abstract", "") != before.get((journal["id"], key), ""):
                    row["journal_relevance"] = relevance(row["title"], row.get("abstract", ""), row.get("article_type", ""), row.get("doi"))
                    recovered += 1
                if row.get("journal_relevance", {}).get("status") in ("relevant", "pending"):
                    items.append(_public_item(row, journal, now))
            counts = {kind: sum(r.get("journal_relevance", {}).get("status") == kind for r in records.values())
                      for kind in ("relevant", "pending", "excluded")}
            state["journals"][journal["id"]]["counters"] = counts
            health["counters"] = {**health.get("counters", {}), **counts, "abstracts_recovered": recovered}
            health["count"] = counts["relevant"] + counts["pending"]
        # Receipt contains public aggregate numbers, never response bodies.
        state["metadata_recovery"] = receipt
    items.sort(key=lambda row: (row.get("published_at") or "", row["id"]), reverse=True)
    return items, statuses, registry, state
