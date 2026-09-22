"""Filtering Engine - Filters and prioritizes companies for research."""

from __future__ import annotations

from typing import Callable

from ..data_models import CompanyAnalysis
from ..utils import Config, FilteringError


class FilteringEngine:
    """Filters and prioritizes companies based on criteria."""
    
    def __init__(self, config: Config) -> None:
        self.config = config

    def filter_by_priority(
        self, companies: list[CompanyAnalysis], priority: str
    ) -> list[CompanyAnalysis]:
        """Filter companies by research priority."""
        valid_priorities = {"DEEP_DIVE", "WATCH", "PASS", "NEEDS_DATA", "NEEDS_VALUATION", "NO_CONCALL", "VERIFY_MCAP", "INELIGIBLE"}
        if priority not in valid_priorities:
            raise FilteringError(f"Invalid priority: {priority}. Must be one of {valid_priorities}")
        return [c for c in companies if c.research_priority == priority]

    def filter_by_score(
        self, companies: list[CompanyAnalysis], min_score: int, max_score: int | None = None
    ) -> list[CompanyAnalysis]:
        """Filter companies by score range."""
        if min_score < 0 or (max_score is not None and max_score < min_score):
            raise FilteringError("Invalid score range")
        
        result = [c for c in companies if c.raw_score >= min_score]
        if max_score is not None:
            result = [c for c in result if c.raw_score <= max_score]
        return result

    def filter_by_confidence(
        self, companies: list[CompanyAnalysis], confidence: str
    ) -> list[CompanyAnalysis]:
        """Filter companies by confidence level."""
        valid = {"high", "medium", "low"}
        if confidence not in valid:
            raise FilteringError(f"Invalid confidence: {confidence}. Must be one of {valid}")
        return [c for c in companies if c.confidence == confidence]

    def filter_by_market_cap(
        self, companies: list[CompanyAnalysis], min_cr: float | None = None, max_cr: float | None = None
    ) -> list[CompanyAnalysis]:
        """Filter companies by market cap range."""
        result = companies
        if min_cr is not None:
            result = [c for c in result if c.market_cap_cr is not None and c.market_cap_cr >= min_cr]
        if max_cr is not None:
            result = [c for c in result if c.market_cap_cr is not None and c.market_cap_cr <= max_cr]
        return result

    def filter_verified_only(self, companies: list[CompanyAnalysis]) -> list[CompanyAnalysis]:
        """Filter to companies with verified market cap."""
        return [c for c in companies if c.market_cap_verified]

    def filter_by_custom(
        self, companies: list[CompanyAnalysis], predicate: Callable[[CompanyAnalysis], bool]
    ) -> list[CompanyAnalysis]:
        """Filter using custom predicate function."""
        return [c for c in companies if predicate(c)]

    def sort_by_priority_score(self, companies: list[CompanyAnalysis]) -> list[CompanyAnalysis]:
        """Sort by research priority and score."""
        return sorted(
            companies,
            key=lambda item: (
                item.research_priority == "DEEP_DIVE",
                item.research_priority == "WATCH",
                item.research_priority == "NEEDS_VALUATION",
                item.market_cap_verified,
                item.raw_score,
            ),
            reverse=True,
        )

    def get_deep_dives(self, companies: list[CompanyAnalysis]) -> list[CompanyAnalysis]:
        """Get all DEEP_DIVE candidates."""
        return self.sort_by_priority_score(
            self.filter_by_priority(companies, "DEEP_DIVE")
        )

    def get_watch_list(self, companies: list[CompanyAnalysis]) -> list[CompanyAnalysis]:
        """Get WATCH candidates."""
        return self.sort_by_priority_score(
            self.filter_by_priority(companies, "WATCH")
        )

    def get_needs_data(self, companies: list[CompanyAnalysis]) -> list[CompanyAnalysis]:
        """Get companies needing more data."""
        return self.sort_by_priority_score(
            self.filter_by_priority(companies, "NEEDS_DATA")
        )
