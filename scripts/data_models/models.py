"""Data models for Alpha Finder research system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """Single piece of evidence from a document."""
    category: str
    signal: str
    points: int
    source: str
    snippet: str


@dataclass
class DocumentAnalysis:
    """Analysis result for a single document."""
    path: str
    document_type: str
    period: str
    text_chars: int
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ValuationScenario:
    """Transparent target-year valuation based on disclosed assumptions."""

    status: str
    target_year: str = ""
    projected_revenue_cr: float | None = None
    projected_opm_pct: float | None = None
    projected_pat_cr: float | None = None
    projected_eps: float | None = None
    low_pe: float | None = None
    high_pe: float | None = None
    fair_value_low: float | None = None
    fair_value_high: float | None = None
    current_price: float | None = None
    upside_low_pct: float | None = None
    upside_high_pct: float | None = None
    source: str = ""
    notes: str = ""
    scenario: str = "base"
    current_eps: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    assumptions_verified: bool = False


@dataclass
class MarketCapSnapshot:
    """Auditable market-cap calculation, never a silently trusted number."""

    market_cap_cr: float | None = None
    last_price: float | None = None
    shares_outstanding_cr: float | None = None
    as_of: str = ""
    source: str = ""
    verified: bool = False


@dataclass
class ResearchMemo:
    """Evidence-grounded company memo; no unsupported forecasts are invented."""

    summary: str = ""
    document_coverage: list[str] = field(default_factory=list)
    future_signals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class CompanyAnalysis:
    """Complete analysis result for a company."""
    symbol: str
    name: str
    market_cap_cr: float | None
    market_cap_verified: bool
    documents: list[DocumentAnalysis]
    raw_score: int
    confidence: str
    coverage_status: str
    research_priority: str
    positive_points: int
    risk_penalty: int
    market_cap_snapshot: MarketCapSnapshot = field(default_factory=MarketCapSnapshot)
    memo: ResearchMemo = field(default_factory=ResearchMemo)
    sector: str = "Unknown"
    industry: str = "Unknown"
    valuation: ValuationScenario = field(
        default_factory=lambda: ValuationScenario(status="MISSING_INPUTS")
    )


@dataclass(frozen=True)
class Filing:
    """Filing record from NSE/BSE."""
    exchange: str
    symbol: str
    filing_id: str
    filed_at: str
    title: str
    description: str
    document_type: str
    url: str
    bse_code: str = ""
