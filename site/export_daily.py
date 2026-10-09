"""Reuse upstream retrieval, Zotero ranking and TLDR generation without SMTP."""
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


def public_paper(p):
    score = getattr(p, "score", None)
    if score is not None:
        score = float(score)
        if not math.isfinite(score):
            score = None
    return {
        "source": str(p.source), "title": str(p.title), "url": str(p.url),
        "authors": list(p.authors or []), "abstract": str(p.abstract or ""),
        "summary": str(p.tldr or ""), "pdf_url": getattr(p, "pdf_url", None),
        "affiliations": list(getattr(p, "affiliations", None) or []),
        "zotero_score": score,
    }


def export(papers, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
               "run_id": os.environ.get("GITHUB_RUN_ID"),
               "papers": [public_paper(p) for p in papers]}
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(destination)


def main():
    upstream = Path.cwd()
    sys.path.insert(0, str(upstream / "src"))
    from zotero_arxiv_daily import executor
    from zotero_arxiv_daily.main import main as upstream_main
    def run_export_only(self):
        corpus = self.filter_corpus(self.fetch_zotero_corpus())
        if not corpus:
            raise RuntimeError("Zotero returned no usable papers; archive was not replaced")
        papers = []
        raw_lookup = {}
        fetch_full_text = getattr(self.config.executor, "fetch_full_text", False)
        for source, retriever in self.retrievers.items():
            executor.logger.info("Retrieving {} papers", source)
            if source == "arxiv" and hasattr(retriever, "_retrieve_raw_papers"):
                from zotero_arxiv_daily.protocol import Paper
                raw = retriever._retrieve_raw_papers()
                for result in raw:
                    raw_lookup[result.entry_id] = (retriever, result)
                    papers.append(Paper(source=source, title=result.title,
                                        authors=[a.name for a in result.authors],
                                        abstract=result.summary, url=result.entry_id,
                                        pdf_url=result.pdf_url))
            else:
                papers.extend(retriever.retrieve_papers())
        ranked = self.reranker.rerank(papers, corpus) if papers else []
        ranked = ranked[:self.config.executor.max_paper_num]
        for index, paper in enumerate(ranked):
            if fetch_full_text and paper.url in raw_lookup:
                retriever, raw = raw_lookup[paper.url]
                try:
                    enriched = retriever.convert_to_paper(raw)
                    enriched.score = paper.score
                    paper = ranked[index] = enriched
                except Exception as error:
                    executor.logger.info("Full text unavailable ({}); using abstract", type(error).__name__)
            paper.generate_tldr(self.openai_client, self.config.llm)
            paper.generate_affiliations(self.openai_client, self.config.llm)
        export(ranked, os.environ["AI4S_PAPER_EXPORT"])
        executor.logger.info("Exported {} papers for AI4S Hot; SMTP is disabled", len(ranked))

    executor.Executor.run = run_export_only
    # Imported Hydra entrypoints resolve relative config paths as packages.
    # Force the checked-out upstream config directory instead.
    original_argv = sys.argv
    sys.argv = [original_argv[0], *original_argv[1:], "--config-path", str(upstream / "config")]
    try:
        upstream_main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()
