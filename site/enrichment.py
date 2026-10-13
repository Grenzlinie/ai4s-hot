"""Bounded public evidence for summaries; no private references or raw CLI output."""
from datetime import date, datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import requests
import trafilatura
import yaml

DEFAULTS = {"enabled": False, "max_items": 8, "max_chars": 12000,
            "timeout": 12, "bohr_enabled": False, "bohr_daily_calls": 0,
            "bohr_payment_source": "default"}
EXTRA_HOSTS = {"arxiv.org", "www.arxiv.org", "www.nature.com", "idp.nature.com",
               "www.science.org", "huggingface.co", "github.com"}


def settings():
    custom = yaml.safe_load(os.environ.get("CUSTOM_CONFIG", "")) or {}
    configured = custom.get("enrichment", {})
    if not isinstance(configured, dict) or set(configured) - set(DEFAULTS):
        raise ValueError("Invalid enrichment configuration")
    value = {**DEFAULTS, **configured}
    for key in ("enabled", "bohr_enabled"):
        if not isinstance(value[key], bool):
            raise ValueError("Invalid enrichment switch")
    for key, maximum in (("max_items", 24), ("max_chars", 24000), ("timeout", 30), ("bohr_daily_calls", 100)):
        if type(value[key]) is not int or not 0 <= value[key] <= maximum or (key in {"max_chars", "timeout"} and not value[key]):
            raise ValueError("Invalid enrichment bound")
    if value["bohr_payment_source"] not in {"default", "photon", "balance"}:
        raise ValueError("Invalid payment source")
    return value


def reserve(ledger_path, config, today=None):
    """Reserve a whole run's allowance BEFORE Git push and BEFORE any query.

    A crash wastes the reservation, never grants it again. Cloud calls only
    consume this reservation after the workflow successfully pushes the ledger.
    """
    path = Path(ledger_path)
    day = today or datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    limit = config["bohr_daily_calls"] if config["enabled"] and config["bohr_enabled"] else 0
    if not limit or not os.environ.get("BOHR_ACCESS_KEY"):
        return 0
    try:
        ledger = json.loads(path.read_text()) if path.exists() else {"date": day, "reserved": 0}
        if set(ledger) != {"date", "reserved"} or not isinstance(ledger["date"], str) or type(ledger["reserved"]) is not int or ledger["reserved"] < 0:
            return 0
        if date.fromisoformat(ledger["date"]).isoformat() != ledger["date"]:
            return 0
        if ledger["date"] > day:
            return 0
        used = ledger["reserved"] if ledger["date"] == day else 0
        allowance = max(0, limit - used)
        if not allowance:
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"date": day, "reserved": used + allowance}))
        temporary.replace(path)
        return allowance
    except (ValueError, OSError, TypeError):
        return 0


def checked_url(url, hosts):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in hosts or p.username or p.password or p.port not in {None, 443}:
        raise ValueError("URL not in public source allowlist")
    try:
        ipaddress.ip_address(p.hostname)
    except ValueError:
        return url
    raise ValueError("IP addresses are not source domains")


def public_text(url, hosts, config):
    checked_url(url, hosts)
    p = urlsplit(url)
    if p.hostname in {"arxiv.org", "www.arxiv.org"}:
        match = re.fullmatch(r"/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?", p.path)
        if match:
            url = "https://arxiv.org/html/" + match[1]
    for _ in range(4):
        with requests.get(checked_url(url, hosts), timeout=config["timeout"], stream=True,
                          allow_redirects=False, headers={"User-Agent": "AI4S-Hot/1.0"}) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                url = urljoin(url, response.headers.get("Location", ""))
                continue
            response.raise_for_status()
            if response.status_code != 200 or "html" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("No public HTML")
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError("Document exceeds extraction size limit")
                chunks.append(chunk)
            text = trafilatura.extract(b"".join(chunks)) or ""
            if len(text) < 800 or any(s in text[:1000].lower() for s in ("verify you are human", "access denied", "enable javascript and cookies")):
                raise ValueError("Insufficient article evidence")
            clean = urlsplit(url)
            return {"kind": "public_html", "text": text[:config["max_chars"]],
                    "url": urlunsplit((clean.scheme, clean.netloc, clean.path, "", ""))}
    raise ValueError("Too many redirects")


def doi_for(item):
    doi = str(item.get("doi") or "").strip().lower().removeprefix("https://doi.org/")
    if not doi:
        p = urlsplit(item["url"])
        if p.hostname == "doi.org":
            doi = p.path.lstrip("/")
        elif p.hostname == "www.nature.com" and re.fullmatch(r"/articles/s[\w-]+", p.path):
            doi = "10.1038/" + p.path.split("/")[-1]
    return doi if re.fullmatch(r"10\.\d{4,9}/[^\s]+", doi) else None


def graph_text(doi, config):
    command = ["bohr", "lkm", "graph", "--doi", doi, "--yes", "--no-interactive", "-o", "json"]
    if config["bohr_payment_source"] != "default":
        command.extend(["--payment-source", config["bohr_payment_source"]])
    # Spool the CLI envelope privately; never load unbounded stdout into RAM.
    # TemporaryFile is unlinked automatically, including on exceptions.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.DEVNULL, timeout=60, check=False)
        if result.returncode or output.tell() > 2_000_000:
            raise ValueError("Bohrium request failed or response too large")
        output.seek(0)
        payload = json.loads(output.read(2_000_000))
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise ValueError("Invalid Bohrium response")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("Invalid graph items")
    for record in data["items"]:
        if not isinstance(record, dict) or not isinstance(record.get("paper"), dict):
            continue
        if str(record["paper"].get("doi", "")).strip().lower() != doi:
            continue
        graph = record.get("graph")
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            continue
        nodes = [n for n in graph["nodes"] if isinstance(n, dict) and isinstance(n.get("content"), str)]
        # Include conclusions and limitations before background questions.
        priority = {"conclusion": 0, "weak_point": 1, "highlight": 2, "reasoning_steps": 3, "subproblem": 4}
        nodes.sort(key=lambda n: priority.get(n.get("kind"), 5))
        text = "\n".join(f"[{n.get('kind', 'unknown')}] {n['content']}" for n in nodes)
        if text.strip():
            return {"kind": "bohr_knowledge_graph", "text": text[:config["max_chars"]], "url": "https://doi.org/" + doi}
    raise ValueError("No exact DOI graph match")


def enrich(items, sources, config=None, allowance=None):
    config = config or settings()
    receipt = {"status": "disabled", "attempted": 0, "public_html": 0, "bohr_graph": 0, "fallback": 0, "bohr_calls": 0}
    evidence = {}
    if not config["enabled"]:
        return evidence, receipt
    receipt["status"] = "ok"
    hosts = EXTRA_HOSTS | {urlsplit(s.get("url", "")).hostname for s in sources}
    # Only workflow-provided prepaid reservation is consumed; local default is 0.
    try:
        allowance = int(os.environ.get("BOHR_CALL_ALLOWANCE", "0")) if allowance is None else allowance
        remaining = min(max(0, allowance), config["bohr_daily_calls"])
    except (ValueError, TypeError):
        remaining = 0
    candidates = [p for p in items if not p.get("summary")]
    candidates.sort(key=lambda p: (p.get("group") == "science", p.get("published_at") or p.get("first_seen", "")), reverse=True)
    for item in candidates[:config["max_items"]]:
        receipt["attempted"] += 1
        content = None
        try:
            content = public_text(item["url"], hosts, config)
            receipt["public_html"] += 1
        except Exception:
            doi = doi_for(item)
            if doi and config["bohr_enabled"] and remaining and os.environ.get("BOHR_ACCESS_KEY"):
                remaining -= 1
                receipt["bohr_calls"] += 1
                try:
                    content = graph_text(doi, config)
                    receipt["bohr_graph"] += 1
                except Exception:
                    pass
        if content:
            content["sha256"] = hashlib.sha256(content["text"].encode()).hexdigest()
            evidence[item["id"]] = content
        else:
            receipt["fallback"] += 1
    if receipt["fallback"]:
        receipt["status"] = "partial"
    return evidence, receipt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reserve", required=True)
    args = parser.parse_args()
    print(reserve(args.reserve, settings()))
