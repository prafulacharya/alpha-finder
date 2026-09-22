"""Alpha Finder - Evidence-first research prioritization system.

INVESTMENT THESIS:
==================
Today's stock price = Result of the last 2 years of company management actions.

Our mission: Find companies where the NEXT 2 YEARS of growth are already VISIBLE
in their filings through:
  • Order books (future revenue commitments)
  • Capacity expansion (tomorrow's growth capacity visible today)
  • Margin improvements (operating leverage emerging)
  • Management strategic vision (capital allocation direction)
  • Product/service expansion (new revenue pipes)

Why? Because the market reprices these stocks 12-18 months AFTER we identify them.

Read: scripts/INVESTMENT_PHILOSOPHY.md for complete thesis explanation.

Examples:
  ★ AARON: 30 pts (DEEP_DIVE) - Order book ₹1,309 Cr, capacity expansion live
  ★ AARTECH: 26 pts (WATCH) - Margin expansion 10-15% YoY, new customers
  ★ INA: 38 pts (needs market cap verification) - Strongest forward indicators

The system automatically detects 50+ evidence signals tied to forward performance
indicators (not traditional ratios like P/E or debt-to-equity).
"""

from .data_models import (
    CompanyAnalysis,
    DocumentAnalysis,
    Evidence,
    Filing,
)
from .engines import (
    AnalysisEngine,
    CleaningEngine,
    CrawlerEngine,
    FilteringEngine,
)
from .orchestrator import ResearchOrchestrator
from .utils import Config

__version__ = "2.0.0"
__all__ = [
    "Config",
    "ResearchOrchestrator",
    "CrawlerEngine",
    "CleaningEngine",
    "AnalysisEngine",
    "FilteringEngine",
    "CompanyAnalysis",
    "DocumentAnalysis",
    "Evidence",
    "Filing",
]
