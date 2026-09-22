"""Configuration management for Alpha Finder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import (
    BSE_CODE_CACHE_PATH,
    DEFAULT_CRAWL_SEGMENT,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MIN_MARKET_CAP_CR,
    DEFAULT_MARKET_CAP_LIMIT_CR,
    DEFAULT_MAX_DOCUMENTS_PER_COMPANY,
    DEFAULT_REQUEST_DELAY_SECONDS,
    DEFAULT_UNIVERSE_MAX_QUOTE_LOOKUPS,
    FILING_INDEX,
    OUTPUT_JSON,
    OUTPUT_MEMOS_DIR,
    OUTPUT_REPORT,
    SOURCES_PATH,
    TRANSCRIPT_DIR,
    UNIVERSE_PARQUET_PATH,
    UNIVERSE_PATH,
    VALUATION_INPUTS_PATH,
)


@dataclass
class Config:
    """Central configuration for the system."""
    
    # Crawler settings
    min_market_cap_cr: float = DEFAULT_MIN_MARKET_CAP_CR
    market_cap_limit_cr: float = DEFAULT_MARKET_CAP_LIMIT_CR
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    max_documents_per_company: int = DEFAULT_MAX_DOCUMENTS_PER_COMPANY
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS
    crawl_segment: str = DEFAULT_CRAWL_SEGMENT
    universe_max_quote_lookups: int = DEFAULT_UNIVERSE_MAX_QUOTE_LOOKUPS
    max_companies: int | None = None
    symbols: tuple[str, ...] = ()
    bse_only: bool = False
    
    # Data paths
    universe_path: str = UNIVERSE_PATH
    universe_parquet_path: str = UNIVERSE_PARQUET_PATH
    bse_code_cache_path: str = BSE_CODE_CACHE_PATH
    transcript_dir: str = TRANSCRIPT_DIR
    sources_path: str = SOURCES_PATH
    filing_index_path: str = FILING_INDEX
    valuation_inputs_path: str = VALUATION_INPUTS_PATH
    market_cap_audit_path: str = "data/inputs/market_cap_audit.csv"
    
    # Output paths
    output_json: str = OUTPUT_JSON
    output_report: str = OUTPUT_REPORT
    output_memos_dir: str = OUTPUT_MEMOS_DIR
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.min_market_cap_cr < 0:
            raise ValueError("min_market_cap_cr must be non-negative")
        if self.market_cap_limit_cr <= 0:
            raise ValueError("market_cap_limit_cr must be positive")
        if self.min_market_cap_cr >= self.market_cap_limit_cr:
            raise ValueError("min_market_cap_cr must be below market_cap_limit_cr")
        if self.lookback_days < 1:
            raise ValueError("lookback_days must be >= 1")
        if self.max_documents_per_company < 1:
            raise ValueError("max_documents_per_company must be >= 1")
        if self.request_delay_seconds < 0:
            raise ValueError("request_delay_seconds must be non-negative")
        if self.max_companies is not None and self.max_companies < 1:
            raise ValueError("max_companies must be >= 1")
    
    def ensure_directories(self) -> None:
        """Create required directories."""
        Path(self.transcript_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(self.output_report).parent.mkdir(parents=True, exist_ok=True)
        Path(self.output_memos_dir).mkdir(parents=True, exist_ok=True)
