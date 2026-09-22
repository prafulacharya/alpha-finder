"""Analysis Engine - Scores companies based on evidence signals."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from ..data_models import CompanyAnalysis, DocumentAnalysis, Evidence, MarketCapSnapshot, ResearchMemo
from ..utils import Config, AnalysisError
from ..utils.constants import SIGNALS
from .cleaning_engine import CleaningEngine
from .valuation_engine import ValuationEngine


class AnalysisEngine:
    """Analysis Engine - Scores companies based on evidence signals.

INVESTMENT PHILOSOPHY:
======================
Today's stock price = Result of last 2 years of company decisions.

We search for LEADING INDICATORS of future profitability, not lagging indicators:

LEADING INDICATORS (We Search For):
  ✓ Order book (future revenue commitments)
  ✓ Capacity expansion (tomorrow's revenue capacity visible today)
  ✓ Margin improvement (operating leverage visible)
  ✓ Management vision & strategic initiatives
  ✓ Product expansion & new markets

Why? Because the market will reprice once these become ACTUAL results
(12-18 months later). We want to find the thesis before the market sees it.

LAGGING INDICATORS (We use as a check, never as the thesis):
  ✗ Current Ratio (past balance sheet)
  • Trailing P/E (describes current earnings, not future execution)
  ✗ Debt-to-Equity (only matters if execution fails)
  ✗ Historical Growth (last year doesn't predict next year)
  ✗ Dividend Yield (for mature, not growth companies)

Example: AARON Industries
- Score: 30/100 (DEEP_DIVE candidate)
- Order book: ₹1,309 Cr (2+ years visibility)
- Capacity: New production line operational Q1 FY26
- Margin: EBITDA 18% → 21% (expansion visible)
- Result: When Q2/Q3 results show order conversion to revenue,
  market reprices stock 30-50% higher.

Our job: Find these thesis-plays 12 months before the market sees them.
"""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.cleaning_engine = CleaningEngine(config)
        self.valuation_engine = ValuationEngine(config)

    @staticmethod
    def infer_symbol(path: Path) -> str:
        """Extract symbol from filename."""
        filename = path.stem.upper()
        return re.split(r"[_\-.]", filename, maxsplit=1)[0]

    @staticmethod
    def classify_document(text: str) -> str:
        """Classify document type from content."""
        sample = text[:12000].lower()
        if "conference call" in sample or "earnings call" in sample or "transcript" in sample:
            return "concall_transcript"
        if "investor presentation" in sample or "corporate presentation" in sample:
            return "investor_presentation"
        if "annual report" in sample:
            return "annual_report"
        if "audited financial results" in sample or "unaudited financial results" in sample:
            return "financial_results"
        return "exchange_filing"

    @staticmethod
    def infer_period(text: str) -> str:
        """Extract reporting period from text."""
        sample = text[:16000].upper().replace("\n", " ")
        
        # Try Q1/Q2/Q3/Q4 format
        quarter = re.search(r"\bQ([1-4])\s*(?:FY)?\s*(2\d)\b", sample)
        if quarter:
            return f"Q{quarter.group(1)} FY{quarter.group(2)}"
        
        # Try quarter ended format
        quarter_long = re.search(
            r"QUARTER(?: AND (?:NINE MONTHS|YEAR))? ENDED\s+"
            r"(?:31(?:ST)?|30(?:TH)?)\s+(MARCH|JUNE|SEPTEMBER|DECEMBER)\s*,?\s*(20\d{2})",
            sample,
        )
        if quarter_long:
            q_by_month = {"JUNE": "Q1", "SEPTEMBER": "Q2", "DECEMBER": "Q3", "MARCH": "Q4"}
            year = int(quarter_long.group(2))
            fiscal_year = year if quarter_long.group(1) == "MARCH" else year + 1
            return f"{q_by_month[quarter_long.group(1)]} FY{str(fiscal_year)[-2:]}"
        
        # Try fiscal year format
        fy = re.search(r"\bFY\s*(2\d)\b|\bFINANCIAL YEAR\s*(20\d{2})", sample)
        if fy:
            year = fy.group(1) or fy.group(2)[-2:]
            return f"FY{year}"
        
        return "unknown"

    @staticmethod
    def is_question_context(text: str, match: re.Match[str]) -> bool:
        """Detect analyst questions to exclude as factual evidence."""
        sentence_start = max(
            text.rfind(".", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind("\n", 0, match.start()),
        )
        sentence_end_candidates = [
            position
            for position in (
                text.find(".", match.end()),
                text.find("?", match.end()),
                text.find("\n", match.end()),
            )
            if position != -1
        ]
        sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
        sentence = text[sentence_start + 1 : sentence_end + 1].lower()
        
        prompt_words = (
            "can you",
            "could you",
            "would you",
            "wanted to ask",
            "want to ask",
            "what is",
            "how long",
            "please explain",
            "please clarify",
        )
        return "?" in sentence or any(word in sentence for word in prompt_words)

    @staticmethod
    def is_negated_context(text: str, match: re.Match[str]) -> bool:
        """Detect negation before match."""
        before = text[max(0, match.start() - 100) : match.start()]
        return bool(
            re.search(
                r"\b(?:no|not|never|nil|without)\b.{0,80}$|"
                r"\bhas not\b.{0,80}$|\bhave not\b.{0,80}$",
                before,
                flags=re.DOTALL,
            )
        )

    @staticmethod
    def is_hypothetical_context(text: str, match: re.Match[str]) -> bool:
        """Detect hypothetical language."""
        before = text[max(0, match.start() - 220) : match.start()]
        return any(
            phrase in before
            for phrase in (
                "upward factors",
                "downward factors",
                "rating may be upgraded",
                "rating may be downgraded",
                "could lead to an upgrade",
                "could lead to a downgrade",
            )
        )

    def analyze_document(self, path: Path) -> DocumentAnalysis:
        """Analyze single document for evidence signals."""
        try:
            text = self.cleaning_engine.extract_pdf_text(path)
        except Exception as exc:
            raise AnalysisError(f"Failed to analyze {path}") from exc
        
        lowered = self.cleaning_engine.prepare_for_analysis(text)
        evidence: list[Evidence] = []
        
        for category, rules in SIGNALS.items():
            for pattern, points, label in rules:
                candidates = re.finditer(pattern, lowered, flags=re.DOTALL)
                match = next(
                    (
                        candidate
                        for candidate in candidates
                        if not self.is_question_context(lowered, candidate)
                        and not (
                            category == "risk"
                            and self.is_negated_context(lowered, candidate)
                        )
                        and not (
                            points > 0
                            and self.is_hypothetical_context(lowered, candidate)
                        )
                    ),
                    None,
                )
                if match:
                    evidence.append(
                        Evidence(
                            category=category,
                            signal=label,
                            points=points,
                            source=str(path),
                            snippet=self.cleaning_engine.extract_snippet(text, match),
                        )
                    )
        
        return DocumentAnalysis(
            path=str(path),
            document_type=self.classify_document(text),
            period=self.infer_period(text),
            text_chars=len(text),
            evidence=evidence,
        )

    def load_universe(self) -> dict[str, dict]:
        """Load micro-cap universe."""
        universe_path = Path(self.config.universe_path)
        if not universe_path.exists():
            return {}
        
        frame = pd.read_csv(universe_path)
        required = {"Symbol", "Name", "MarketCap_Cr"}
        missing = required.difference(frame.columns)
        if missing:
            raise AnalysisError(f"Universe missing columns: {', '.join(sorted(missing))}")
        
        frame["Symbol"] = frame["Symbol"].astype(str).str.upper().str.strip()
        frame["MarketCap_Cr"] = pd.to_numeric(frame["MarketCap_Cr"], errors="coerce")
        if self.config.symbols:
            frame = frame[frame["Symbol"].isin(self.config.symbols)]
        if self.config.max_companies is not None:
            frame = frame.head(self.config.max_companies)
        return {row["Symbol"]: row.to_dict() for _, row in frame.iterrows()}

    def market_cap_snapshot(self, symbol: str, row: dict | None) -> MarketCapSnapshot:
        """Read a manually reconciled audit row; do not label stale imports verified."""
        audit = Path(self.config.market_cap_audit_path)
        if audit.exists():
            frame = pd.read_csv(audit)
            if {"Symbol", "LastPrice", "SharesOutstandingCr", "AsOf", "Source"}.issubset(frame.columns):
                matches = frame[frame["Symbol"].astype(str).str.upper().str.strip() == symbol]
                if not matches.empty:
                    item = matches.iloc[-1]
                    price = pd.to_numeric(item["LastPrice"], errors="coerce")
                    shares = pd.to_numeric(item["SharesOutstandingCr"], errors="coerce")
                    if pd.notna(price) and pd.notna(shares) and price > 0 and shares > 0:
                        return MarketCapSnapshot(float(price * shares), float(price), float(shares), str(item["AsOf"]), str(item["Source"]), True)
        cap = None if row is None or pd.isna(row["MarketCap_Cr"]) else float(row["MarketCap_Cr"])
        return MarketCapSnapshot(cap, source=str(row.get("MarketCapSource") or "unverified import") if row else "", as_of=str(row.get("MarketCapAsOf") or "") if row else "", verified=False)

    @staticmethod
    def confidence_for(
        documents: list[DocumentAnalysis], market_cap_verified: bool
    ) -> tuple[str, str]:
        """Determine confidence level and coverage status."""
        periods = {doc.period for doc in documents if doc.period != "unknown"}
        has_transcript = any(
            doc.document_type == "concall_transcript" for doc in documents
        )
        has_results = any(
            doc.document_type in {"financial_results", "annual_report"}
            for doc in documents
        )
        
        if market_cap_verified and len(periods) >= 3 and has_transcript and has_results:
            return "high", "3+ periods with transcript and financial statements"
        if market_cap_verified and len(periods) >= 2 and (has_transcript or has_results):
            return "medium", "2 periods with partial source coverage"
        
        missing = []
        if not market_cap_verified:
            missing.append("verified market cap")
        if len(periods) < 3:
            missing.append(f"3 reporting periods ({len(periods)} found)")
        if not has_transcript:
            missing.append("concall transcript")
        if not has_results:
            missing.append("financial results/annual report")
        
        return "low", "missing " + ", ".join(missing)

    def analyze_company(
        self,
        symbol: str,
        files: Iterable[Path],
        universe: dict[str, dict],
    ) -> CompanyAnalysis:
        """Analyze company from all its documents."""
        documents = []
        for path in sorted(files):
            try:
                documents.append(self.analyze_document(path))
            except Exception as exc:
                documents.append(
                    DocumentAnalysis(
                        path=str(path),
                        document_type="unreadable",
                        period="unknown",
                        text_chars=0,
                        evidence=[
                            Evidence(
                                "risk",
                                "document extraction failed",
                                -5,
                                str(path),
                                str(exc),
                            )
                        ],
                    )
                )

        row = universe.get(symbol)
        snapshot = self.market_cap_snapshot(symbol, row)
        market_cap = snapshot.market_cap_cr
        market_cap_verified = (
            market_cap is not None
            and market_cap > self.config.min_market_cap_cr
            and market_cap < self.config.market_cap_limit_cr
            and snapshot.verified
        )
        
        all_evidence = [item for doc in documents for item in doc.evidence]
        evidence_by_signal: dict[str, list[Evidence]] = {}
        for item in all_evidence:
            evidence_by_signal.setdefault(item.signal, []).append(item)

        positive = 0
        penalty = 0
        for items in evidence_by_signal.values():
            representative = max(items, key=lambda item: abs(item.points))
            confirmations = min(3, len({item.source for item in items}) - 1)
            if representative.points > 0:
                positive += representative.points + (confirmations * 2)
            else:
                penalty += abs(representative.points) + (confirmations * 2)

        raw_score = max(0, min(100, positive - penalty))
        confidence, coverage = self.confidence_for(documents, market_cap_verified)

        positive_evidence = [item for item in all_evidence if item.points > 0]
        risk_evidence = [item for item in all_evidence if item.points < 0]
        document_coverage = sorted({doc.document_type for doc in documents})
        future_signals = sorted({item.signal for item in positive_evidence})
        risks = sorted({item.signal for item in risk_evidence})
        evidence_snippets = [
            f"{item.signal}: {item.snippet}"
            for item in sorted(
                all_evidence,
                key=lambda item: abs(item.points),
                reverse=True,
            )[:8]
        ]
        if future_signals:
            summary = (
                f"{symbol} has {len(documents)} analyzed document(s). "
                f"Forward evidence detected: {', '.join(future_signals)}."
            )
        else:
            summary = (
                f"{symbol} has {len(documents)} analyzed document(s), "
                "but no supported forward-looking signal was detected."
            )
        memo = ResearchMemo(
            summary=summary,
            document_coverage=document_coverage,
            future_signals=future_signals,
            risks=risks,
            evidence=evidence_snippets,
        )
        
        if not market_cap_verified:
            priority = "INELIGIBLE" if market_cap is not None else "VERIFY_MCAP"
        elif not any(doc.document_type == "concall_transcript" for doc in documents):
            # Absence is a research finding, not a soft confidence discount.
            priority = "NO_CONCALL"
        elif confidence == "low":
            priority = "NEEDS_DATA"
        elif self.valuation_engine.value(symbol).status != "READY":
            priority = "NEEDS_VALUATION"
        elif raw_score >= 30 and confidence == "high":
            priority = "DEEP_DIVE"
        elif raw_score >= 25:
            priority = "WATCH"
        else:
            priority = "PASS"

        valuation = self.valuation_engine.value(symbol)
        return CompanyAnalysis(
            symbol=symbol,
            name=str(row["Name"]) if row else symbol,
            market_cap_cr=market_cap,
            market_cap_verified=market_cap_verified,
            market_cap_snapshot=snapshot,
            memo=memo,
            documents=documents,
            raw_score=raw_score,
            confidence=confidence,
            coverage_status=coverage,
            research_priority=priority,
            positive_points=positive,
            risk_penalty=penalty,
            sector=str(row.get("Sector") or "Unknown") if row else "Unknown",
            industry=str(row.get("Industry") or "Unknown") if row else "Unknown",
            valuation=valuation,
        )

    def discover_documents(self) -> dict[str, list[Path]]:
        """Discover all documents grouped by symbol."""
        grouped: dict[str, list[Path]] = {}
        transcript_dir = Path(self.config.transcript_dir)
        
        if not transcript_dir.exists():
            return grouped
        
        for path in transcript_dir.rglob("*.pdf"):
            grouped.setdefault(self.infer_symbol(path), []).append(path)
        
        return grouped
