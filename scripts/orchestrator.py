"""Orchestrator - Coordinates all engines for research pipeline.

INVESTMENT THESIS:
==================
Today's stock price = Result of the last 2 years of company management decisions.

Our pipeline finds companies where the NEXT 2 YEARS of decisions are already
VISIBLE TODAY in their filings.

We search for LEADING INDICATORS:
  • Order book commitments (actual customers, binding revenue)
  • Capacity expansion projects (revenue scaling visible)
  • Margin improvement trends (operating leverage emerging)
  • Management strategic initiatives (future direction visible)
  • Product/service expansion plans (new revenue pipes)

Why this works:
  1. Discovery Phase (NOW): We identify thesis 12 months before market sees it
  2. Validation Phase (3-6 months): Quarterly results confirm order → revenue conversion
  3. Repricing Phase (6-18 months): Market discovers the growth, stock re-rates
  4. Exit Phase (18-36 months): Risk/reward becomes unfavorable, redeploy capital

Examples from current pipeline:
  ★ AARON: Order book ₹1,309 Cr visible → 2+ years revenue certainty
  ★ AARTECH: New capacity + customer wins + margin expansion → 25+ pt score
  ★ INA: 38 pt score, just needs market cap verification

The system automatically detects these signals across 50+ patterns
and ranks companies by research priority.

See: scripts/INVESTMENT_PHILOSOPHY.md for detailed thesis explanation.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .data_models import CompanyAnalysis
from .engines import AnalysisEngine, CrawlerEngine, FilteringEngine
from .utils import Config


class ResearchOrchestrator:
    """Orchestrates the complete research pipeline."""
    
    def __init__(self, config: Config) -> None:
        config.validate()
        config.ensure_directories()
        self.config = config
        
        self.crawler = CrawlerEngine(config)
        self.analyzer = AnalysisEngine(config)
        self.filter_engine = FilteringEngine(config)

    def purge_old_data(self) -> None:
        """Purge old transcripts and filing index to ensure discovery of fresh data."""
        import shutil
        print("Purging old transcripts and filing index...")
        transcript_dir = Path(self.config.transcript_dir)
        index_file = Path(self.config.filing_index_path)
        
        if transcript_dir.exists():
            shutil.rmtree(transcript_dir)
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        if index_file.exists():
            index_file.unlink()
        print("Purge complete. Starting fresh discovery.")

    def run_full_pipeline(self, purge: bool = False) -> list[CompanyAnalysis]:
        """Execute complete research pipeline: crawl → analyze → prioritize."""
        if purge:
            self.purge_old_data()

        # Phase 1: Crawl exchanges for filings
        print("Phase 1: Crawling exchanges...")
        crawl_stats = self.crawler.crawl()
        print(f"  Discovered: {crawl_stats['discovered']} filings")
        print(f"  Downloaded: {crawl_stats['downloaded']} new documents")

        # Phase 2: Analyze documents
        print("\nPhase 2: Analyzing documents...")
        universe = self.analyzer.load_universe()
        documents = self.analyzer.discover_documents()
        symbols = sorted(set(universe).union(documents))
        if self.config.symbols:
            symbols = [symbol for symbol in symbols if symbol in self.config.symbols]
        if self.config.max_companies is not None:
            symbols = symbols[: self.config.max_companies]
        
        results = [
            self.analyzer.analyze_company(symbol, documents.get(symbol, []), universe)
            for symbol in symbols
            if documents.get(symbol)
        ]
        print(f"  Analyzed: {len(results)} companies")

        # Phase 3: Filter and prioritize
        print("\nPhase 3: Filtering and prioritizing...")
        results = self.filter_engine.sort_by_priority_score(results)
        deep_dives = len(self.filter_engine.filter_by_priority(results, "DEEP_DIVE"))
        watch = len(self.filter_engine.filter_by_priority(results, "WATCH"))
        print(f"  Deep Dives: {deep_dives}")
        print(f"  Watch List: {watch}")

        # Phase 4: Write outputs
        print("\nPhase 4: Writing outputs...")
        self.write_outputs(results)
        
        return results

    def run_analysis_only(self) -> list[CompanyAnalysis]:
        """Run analysis on existing documents without crawling."""
        universe = self.analyzer.load_universe()
        documents = self.analyzer.discover_documents()
        symbols = sorted(set(universe).union(documents))
        if self.config.symbols:
            symbols = [symbol for symbol in symbols if symbol in self.config.symbols]
        if self.config.max_companies is not None:
            symbols = symbols[: self.config.max_companies]
        
        results = [
            self.analyzer.analyze_company(symbol, documents.get(symbol, []), universe)
            for symbol in symbols
            if documents.get(symbol)
        ]
        results = self.filter_engine.sort_by_priority_score(results)
        self.write_outputs(results)
        return results

    def write_outputs(self, results: list[CompanyAnalysis]) -> None:
        """Write analysis results to JSON and markdown."""
        # JSON output
        output_json = Path(self.config.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(
                [asdict(result) for result in results],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Markdown report
        self._write_markdown_report(results)
        self._write_company_memos(results)

    def _write_company_memos(self, results: list[CompanyAnalysis]) -> None:
        """Write one evidence-grounded Markdown memo per analyzed company."""
        memo_dir = Path(self.config.output_memos_dir)
        memo_dir.mkdir(parents=True, exist_ok=True)
        active_symbols = set()
        for company in results:
            active_symbols.add(company.symbol)
            memo = company.memo
            lines = [
                f"# {company.symbol} Research Memo",
                "",
                f"**Company:** {company.name}",
                f"**Market cap:** {company.market_cap_cr:,.2f} Cr" if company.market_cap_cr else "**Market cap:** unknown",
                f"**Priority:** {company.research_priority}",
                f"**Score:** {company.raw_score}/100",
                "",
                "> Evidence summary only. This is not investment advice. Forecasts are included only when sourced assumptions exist.",
                "",
                "## Summary",
                memo.summary,
                "",
                "## Document Coverage",
                *(
                    [f"- {item}" for item in memo.document_coverage]
                    if memo.document_coverage
                    else ["- None"]
                ),
                "",
                "## Forward Signals",
                *(
                    [f"- {item}" for item in memo.future_signals]
                    if memo.future_signals
                    else ["- None detected"]
                ),
                "",
                "## Risks",
                *(
                    [f"- {item}" for item in memo.risks]
                    if memo.risks
                    else ["- None detected"]
                ),
                "",
                "## Valuation",
                f"- Status: {company.valuation.status}",
                f"- Forward P/E: {company.valuation.forward_pe:.1f}x" if company.valuation.forward_pe is not None else "- Forward P/E: not available",
                f"- Fair value: ₹{company.valuation.fair_value_low:.2f}-₹{company.valuation.fair_value_high:.2f}" if company.valuation.status == "READY" else "- Fair value: not available",
                "",
                "## Source Evidence",
                *(
                    [f"- {item}" for item in memo.evidence]
                    if memo.evidence
                    else ["- No evidence extracted"]
                ),
                "",
            ]
            (memo_dir / f"{company.symbol}.md").write_text("\n".join(lines), encoding="utf-8")

        for path in memo_dir.glob("*.md"):
            if path.stem not in active_symbols:
                path.unlink()

    def _write_markdown_report(self, results: list[CompanyAnalysis]) -> None:
        """Generate markdown watchlist report."""
        output_report = Path(self.config.output_report)
        output_report.parent.mkdir(parents=True, exist_ok=True)
        
        generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        rows: list[str] = []

        def cell(value: object) -> str:
            return str(value).replace("|", "\\|").replace("\n", " ")

        for company in results:
            market_cap_str = (
                f"{company.market_cap_cr:,.2f}"
                if company.market_cap_cr
                else "unknown"
            )
            has_concall = any(doc.document_type == "concall_transcript" for doc in company.documents)
            valuation = company.valuation
            fair_value = (
                f"₹{valuation.fair_value_low:.2f}-₹{valuation.fair_value_high:.2f}"
                if valuation.status == "READY" else valuation.status
            )
            forward_pe = f"{valuation.forward_pe:.1f}x" if valuation.forward_pe is not None else "not available"
            cells = (
                company.symbol,
                company.industry,
                market_cap_str,
                "verified" if company.market_cap_snapshot.verified else "needs audit",
                company.raw_score,
                company.research_priority,
                "yes" if has_concall else "NO",
                valuation.status,
                forward_pe,
                fair_value,
            )
            rows.append("| " + " | ".join(cell(value) for value in cells) + " |")

        output_report.write_text(
            "# Alpha Finder Research Queue\n\n"
            f"Generated: {generated}  \n"
            f"Market-cap range: ₹{self.config.min_market_cap_cr:,.0f} < market cap < ₹{self.config.market_cap_limit_cr:,.0f} Cr  \n\n"
            "> Research queue only, not investment advice. A score is not a buy signal.\n\n"
            "| Symbol | Industry | Market Cap (Cr) | Market Cap | Score | Priority | Concall | Valuation | Forward P/E | Fair Value (₹) |\n"
            "|---|---|---:|---|---:|---|---|---|---:|---|\n"
            + "\n".join(rows)
            + "\n", encoding="utf-8")

        memo_sections = []
        for company in results:
            memo = company.memo
            memo_sections.append(
                "\n## " + cell(company.symbol) + "\n\n"
                + cell(memo.summary) + "\n\n"
                + "**Documents:** " + (", ".join(memo.document_coverage) or "none") + "\n\n"
                + "**Forward signals:** " + (", ".join(memo.future_signals) or "none detected") + "\n\n"
                + "**Risks:** " + (", ".join(memo.risks) or "none detected") + "\n\n"
                + "**Evidence:**\n"
                + "\n".join(f"- {cell(item)}" for item in memo.evidence)
                + "\n"
            )
        with output_report.open("a", encoding="utf-8") as report:
            report.write("\n# Company Memos\n" + "".join(memo_sections))
