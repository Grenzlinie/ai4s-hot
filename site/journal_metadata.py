"""Bounded free public abstract enrichment. State mutations are persisted by caller.

No LLM, Bohrium, API key, local credential, full text or paid endpoint is used.
HTTP calls (including redirects) share a persisted Asia/Shanghai daily budget.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import re
from urllib.parse import quote, urljoin, urlsplit
from zoneinfo import ZoneInfo

from lxml import etree, html as lhtml
import requests
import journals

UTC = timezone.utc
DEFAULTS = {"enabled": True, "max_requests": 20, "max_candidates": 10}
PUBLISHER_HOSTS = frozenset({"www.nature.com", "nature.com", "www.science.org", "science.org",
    "advanced.onlinelibrary.wiley.com", "onlinelibrary.wiley.com", "www.sciencedirect.com",
    "sciencedirect.com", "www.cell.com", "cell.com"})
API_HOSTS = frozenset({"api.crossref.org", "api.openalex.org"})
MATERIAL_JOURNALS = frozenset({"nature-materials", "advanced-materials", "advanced-energy-materials",
    "advanced-functional-materials", "acta-materialia", "matter"})
HINT = re.compile(r"\b(?:AI|learning|neural|autonomous|atomistic|interatomic|generative|bayesian|foundation model|language model|knowledge graph)\b", re.I)
BAD_ABSTRACT = re.compile(r"(?:just a moment|verify (?:that )?you are human|enable javascript|access denied|captcha|subscribe to (?:read|access)|sign in to (?:read|access)|purchase (?:this|the) article|get full access|this (?:journal|website) (?:publishes|uses)|a multidisciplinary journal|accept (?:all )?cookies)", re.I)
HEADERS = {"User-Agent": "AI4S-Hot/1.0 (https://github.com/Grenzlinie/ai4s-hot)",
           "Accept": "application/json,text/html;q=0.9"}


class MetadataUnavailable(ValueError):
    """A public source did not provide a usable, verified abstract."""


def abstract_text(value, title=""):
    if not isinstance(value, str):
        return None
    text = journals.clean_abstract(value, title)
    if not text or BAD_ABSTRACT.search(text):
        return None
    # A long title followed only by a journal name/date is not an abstract.
    cleaned, title_key = journals.title_key(text), journals.title_key(title)
    if title_key and cleaned.startswith(title_key) and len(cleaned) - len(title_key) < 100:
        return None
    return text[:6000]


def _safe_url(url, *, api=False):
    parsed = urlsplit(str(url))
    allowed = API_HOSTS if api else PUBLISHER_HOSTS
    try:
        if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise MetadataUnavailable("unsupported_public_url")
    except ValueError as error:
        raise MetadataUnavailable("unsupported_public_url") from error
    return str(url)


class Budget:
    def __init__(self, state, limit, now):
        self.used = 0
        self.limit = limit
        self.date = now.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
        has_ledger = "metadata_budget" in state
        existing = state.get("metadata_budget", {})
        if not isinstance(existing, dict):
            raise ValueError("invalid_metadata_budget_mapping")
        if has_ledger and set(existing) != {"date", "requests"}:
            raise ValueError("invalid_metadata_budget_fields")
        old_day, old_requests = existing.get("date"), existing.get("requests", 0)
        if has_ledger:
            try:
                valid_date = isinstance(old_day, str) and date.fromisoformat(old_day).isoformat() == old_day
            except (ValueError, TypeError):
                valid_date = False
            if not valid_date or old_day > self.date:
                raise ValueError("invalid_metadata_budget_date")
        if isinstance(old_requests, bool) or not isinstance(old_requests, int) or old_requests < 0:
            raise ValueError("invalid_metadata_budget_count")
        self.ledger = {"date": self.date, "requests": old_requests if old_day == self.date else 0}
        state["metadata_budget"] = self.ledger

    @property
    def available(self):
        return max(0, self.limit - self.ledger["requests"])

    def reserve(self):
        if not self.available:
            raise MetadataUnavailable("metadata_request_budget_exhausted")
        self.used += 1
        self.ledger["requests"] += 1


def _request(url, budget, *, params=None, api=False):
    """No hidden retries; redirects count and can only reach public allowlist."""
    for redirect in range(3):
        url = _safe_url(url, api=api)
        budget.reserve()
        # trust_env=False also prevents automatic .netrc credential lookup.
        with requests.Session() as session:
            session.trust_env = False
            with session.get(url, params=params, headers=HEADERS, timeout=(5, 12),
                             stream=True, allow_redirects=False) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location or redirect == 2:
                        raise MetadataUnavailable("publisher_redirect_limit")
                    url, params = urljoin(url, location), None
                    _safe_url(url, api=api)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                expected = ("application/json",) if api else ("text/html", "application/xhtml+xml")
                if not any(kind in content_type for kind in expected):
                    raise MetadataUnavailable("unexpected_metadata_content_type")
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 2_000_000:
                        raise MetadataUnavailable("metadata_response_size_limit")
                return bytes(data), url
    raise MetadataUnavailable("publisher_redirect_limit")


def _crossref(doi, title, budget):
    data, _ = _request("https://api.crossref.org/works/" + quote(doi, safe=""), budget, api=True)
    row = json.loads(data)["message"]
    if not isinstance(row, dict):
        raise MetadataUnavailable("crossref_invalid_record")
    if journals.normalize_doi(row.get("DOI")) != doi:
        raise MetadataUnavailable("crossref_doi_mismatch")
    abstract = abstract_text(row.get("abstract"), title)
    resource = row.get("resource") or {}
    primary = resource.get("primary") if isinstance(resource, dict) else None
    landing = (primary.get("URL") if isinstance(primary, dict) else None) or row.get("URL")
    return abstract, landing


def _inverted_abstract(index):
    if not isinstance(index, dict) or len(index) > 10000:
        return None
    words = {}
    for word, positions in index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            return None
        for position in positions:
            if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position < 20000 or position in words:
                return None
            words[position] = word
    return " ".join(words[p] for p in sorted(words))


def _openalex(candidates, budget):
    """One exact DOI batch; no search endpoint, key or estimated DOI matching."""
    wanted = {c["doi"]: c for c in candidates}
    params = {"filter": "doi:" + "|".join("https://doi.org/" + doi for doi in wanted),
              "per-page": len(wanted), "select": "doi,abstract_inverted_index,primary_location"}
    data, _ = _request("https://api.openalex.org/works", budget, params=params, api=True)
    payload = json.loads(data)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise MetadataUnavailable("openalex_invalid_results")
    result = {}
    for row in payload["results"]:
        if not isinstance(row, dict):
            continue
        doi = journals.normalize_doi(row.get("doi"))
        if doi not in wanted or doi in result:
            continue
        location = row.get("primary_location") or {}
        location = location if isinstance(location, dict) else {}
        result[doi] = (abstract_text(_inverted_abstract(row.get("abstract_inverted_index")), wanted[doi]["row"]["title"]),
                       location.get("landing_page_url"))
    return result


def _jsonld_articles(doc):
    for script in doc.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            data = json.loads(script)
        except (ValueError, TypeError):
            continue
        queue = data if isinstance(data, list) else [data]
        while queue:
            node = queue.pop(0)
            if not isinstance(node, dict):
                continue
            queue.extend(node.get("@graph", []) if isinstance(node.get("@graph"), list) else [])
            kind = node.get("@type", [])
            kind = [kind] if isinstance(kind, str) else kind if isinstance(kind, list) else []
            if any(k in ("ScholarlyArticle", "Article", "MedicalScholarlyArticle") for k in kind):
                yield node


def _identifier_dois(node):
    values = node.get("identifier", [])
    values = values if isinstance(values, list) else [values]
    result = set()
    for value in values:
        if isinstance(value, dict):
            if str(value.get("propertyID", "")).lower() not in ("doi", "https://doi.org"):
                continue
            value = value.get("value")
        doi = journals.normalize_doi(value)
        if doi:
            result.add(doi)
    return result


def publisher_abstract(data, doi, title):
    """Metadata/abstract section only after exact article DOI verification."""
    try:
        doc = lhtml.fromstring(data, parser=lhtml.HTMLParser(no_network=True))
    except (etree.ParserError, etree.XMLSyntaxError, ValueError) as error:
        raise MetadataUnavailable("publisher_invalid_document") from error
    article_nodes = list(_jsonld_articles(doc))
    identifiers = set()
    for meta in doc.xpath('//meta'):
        name = (meta.get("name") or meta.get("property") or "").lower()
        if name in ("citation_doi", "dc.identifier", "dc.identifier.doi", "prism.doi"):
            found = journals.normalize_doi(meta.get("content"))
            if found:
                identifiers.add(found)
    for link in doc.xpath('//link[@rel="canonical"]/@href'):
        parsed = urlsplit(link)
        if parsed.hostname in ("doi.org", "dx.doi.org"):
            found = journals.normalize_doi(link)
            if found:
                identifiers.add(found)
    for node in article_nodes:
        identifiers.update(_identifier_dois(node))
    if identifiers != {doi}:
        raise MetadataUnavailable("publisher_article_doi_not_verified")
    candidates = []
    for name in ("citation_abstract", "dc.description", "og:description"):
        candidates.extend(doc.xpath('//meta[translate(@name,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")=$name or translate(@property,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")=$name]/@content', name=name))
    for node in article_nodes:
        if _identifier_dois(node) == {doi} or (not _identifier_dois(node) and len(article_nodes) == 1):
            candidates.extend(node.get(field) for field in ("abstract", "description") if isinstance(node.get(field), str))
    # Nature's openly visible Abstract section; never arbitrary article body.
    for node in doc.xpath('//*[@id="Abs1-content"] | //section[@data-title="Abstract"]//*[contains(@class,"c-article-section__content")]'):
        candidates.append(node.text_content())
    for value in candidates:
        abstract = abstract_text(value, title)
        if abstract:
            return abstract
    raise MetadataUnavailable("publisher_abstract_unavailable")


def _landing_url(candidate):
    row, doi = candidate["row"], candidate["doi"]
    urls = [candidate.get("landing"), row.get("url")]
    if doi.startswith("10.1038/"):
        urls.append("https://www.nature.com/articles/" + doi.split("/", 1)[1])
    elif doi.startswith("10.1126/"):
        urls.append("https://www.science.org/doi/" + doi)
    elif doi.startswith("10.1002/"):
        urls.append("https://advanced.onlinelibrary.wiley.com/doi/" + doi)
    for url in urls:
        if not url:
            continue
        try:
            return _safe_url(url)
        except MetadataUnavailable:
            pass
    return None


def _settings(config):
    if isinstance(config, list):
        return DEFAULTS.copy(), config
    settings = {**DEFAULTS, **config.get("metadata", {})}
    if set(settings) != set(DEFAULTS) or not isinstance(settings["enabled"], bool):
        raise ValueError("invalid_journal_metadata_settings")
    for field, upper in (("max_requests", 20), ("max_candidates", 20)):
        value = settings[field]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= upper:
            raise ValueError("invalid_journal_metadata_settings:" + field)
    return settings, config.get("journals", [])


def enrich_candidates(state, config, now):
    """Mutate missing public abstracts in state; return anonymous aggregate receipt.

    config accepts full journals.json dict (metadata settings) or registry list.
    Failures persist 1/3/7-day retry times. Caller re-screens and commits state only
    after its full publication pipeline succeeds. Requests never exceed 20/day.
    """
    now = datetime.fromisoformat(journals.date_iso(now))
    settings, registry = _settings(config)
    receipt = {"attempted": 0, "improved": 0, "failed": 0, "skipped": 0,
               "requests": 0, "providers": {"crossref": 0, "openalex": 0, "publisher": 0},
               "skip_reasons": {}, "status": "disabled" if not settings["enabled"] else "ok"}
    if not settings["enabled"]:
        return receipt
    try:
        budget = Budget(state, settings["max_requests"], now)
    except ValueError:
        # Fail closed for enrichment only: do not replace a damaged ledger and
        # do not block the site's independent collection/publication pipeline.
        receipt["status"] = "budget_invalid"
        receipt["remaining_daily_requests"] = 0
        return receipt
    registered = {r["id"] for r in registry}
    def skip(reason):
        receipt["skipped"] += 1
        receipt["skip_reasons"][reason] = receipt["skip_reasons"].get(reason, 0) + 1
    candidates = []
    for journal_id, journal_state in state.get("journals", {}).items():
        if journal_id not in registered:
            continue
        for row in journal_state.get("records", {}).values():
            title = journals.plain(row.get("title"))
            if row.get("journal_relevance", {}).get("status") == "excluded":
                skip("excluded"); continue
            if abstract_text(row.get("abstract"), title):
                skip("has_abstract"); continue
            doi = journals.normalize_doi(row.get("doi") or row.get("url"))
            if not doi:
                skip("no_verified_doi"); continue
            due = journals.date_iso(row.get("metadata_next_attempt_at"))
            if due and datetime.fromisoformat(due) > now:
                skip("retry_backoff"); continue
            priority = 0 if journals.AI.search(title) and journals.MATERIAL.search(title) else 1 if journal_id in MATERIAL_JOURNALS and HINT.search(title) else None
            if priority is None:
                skip("no_materials_ai_title_hint"); continue
            candidates.append({"row": row, "doi": doi, "priority": priority, "journal_id": journal_id})
    candidates.sort(key=lambda c: (c["priority"], -(datetime.fromisoformat(journals.date_iso(c["row"].get("first_seen")) or now.isoformat()).timestamp()), c["doi"]))
    selected = candidates[:settings["max_candidates"]]
    for _ in candidates[len(selected):]:
        skip("candidate_limit")
    pending, attempted = [], []
    def start(candidate):
        row = candidate["row"]
        row["metadata_attempts"] = max(0, int(row.get("metadata_attempts", 0))) + 1
        attempted.append(candidate)
        receipt["attempted"] += 1
    def improve(candidate, text, provider):
        row = candidate["row"]
        row["abstract"] = text.strip()[:6000]
        row["metadata_provider"] = provider
        row["metadata_next_attempt_at"] = None
        row["metadata_updated_at"] = now.isoformat()
        receipt["improved"] += 1
        receipt["providers"][provider] += 1
        candidate["improved"] = True
    errors = (requests.RequestException, MetadataUnavailable, ValueError, KeyError, TypeError, IndexError)
    for candidate in selected:
        if not budget.available:
            skip("daily_request_limit"); continue
        start(candidate)
        candidate["row"]["metadata_provider"] = "crossref"
        try:
            abstract, landing = _crossref(candidate["doi"], candidate["row"]["title"], budget)
            candidate["landing"] = landing
            if abstract:
                improve(candidate, abstract, "crossref")
            else:
                pending.append(candidate)
        except errors:
            pending.append(candidate)
    if pending and budget.available:
        for candidate in pending:
            candidate["row"]["metadata_provider"] = "openalex"
        try:
            results = _openalex(pending, budget)
            for candidate in pending:
                abstract, landing = results.get(candidate["doi"], (None, None))
                if landing:
                    candidate["landing"] = landing
                if abstract:
                    improve(candidate, abstract, "openalex")
        except errors:
            pass
    for candidate in pending:
        if candidate.get("improved") or not budget.available:
            continue
        url = _landing_url(candidate)
        if not url:
            continue
        candidate["row"]["metadata_provider"] = "publisher"
        try:
            data, _ = _request(url, budget)
            improve(candidate, publisher_abstract(data, candidate["doi"], candidate["row"]["title"]), "publisher")
        except errors:
            pass
    for candidate in attempted:
        if candidate.get("improved"):
            continue
        row = candidate["row"]
        days = (1, 3, 7)[min(row["metadata_attempts"] - 1, 2)]
        row["metadata_next_attempt_at"] = (now + timedelta(days=days)).isoformat()
        receipt["failed"] += 1
    receipt["requests"] = budget.used
    receipt["remaining_daily_requests"] = budget.available
    if receipt["failed"]:
        receipt["status"] = "partial"
    return receipt
