"""Unit tests for universe segment classification."""

import unittest
from unittest.mock import patch

import pandas as pd

from scripts.engines.universe_builder import BuildStats, UniverseBuilder
from scripts.engines.crawler_engine import CrawlerEngine
from scripts.data_models import Filing
from scripts.engines.crawler_engine import classify_filing
from scripts.utils.constants import (
    DEFAULT_MIN_MARKET_CAP_CR,
    DEFAULT_MARKET_CAP_LIMIT_CR,
    SEGMENT_CEILING_CR,
    SEGMENT_MICRO_MAX_CR,
    SEGMENT_NANO_MAX_CR,
    classify_segment,
    segments_for_filter,
)


class TestClassifySegment(unittest.TestCase):
    def test_requested_default_market_cap_ceiling(self) -> None:
        self.assertEqual(DEFAULT_MIN_MARKET_CAP_CR, 100)
        self.assertEqual(DEFAULT_MARKET_CAP_LIMIT_CR, 3500)

    def test_nano_boundary(self) -> None:
        self.assertEqual(classify_segment(0), None)
        self.assertEqual(classify_segment(-1), None)
        self.assertEqual(classify_segment(None), None)
        self.assertEqual(classify_segment(99.99), "nano")
        self.assertEqual(classify_segment(SEGMENT_NANO_MAX_CR - 0.01), "nano")

    def test_micro_range(self) -> None:
        self.assertEqual(classify_segment(SEGMENT_NANO_MAX_CR), "micro")
        self.assertEqual(classify_segment(250), "micro")
        self.assertEqual(classify_segment(SEGMENT_MICRO_MAX_CR), "micro")

    def test_small_micro_range(self) -> None:
        self.assertEqual(classify_segment(SEGMENT_MICRO_MAX_CR + 0.01), "small_micro")
        self.assertEqual(classify_segment(750), "small_micro")
        self.assertEqual(classify_segment(1000), "small_micro")
        self.assertEqual(classify_segment(SEGMENT_CEILING_CR), "extended_micro")

    def test_above_ceiling(self) -> None:
        self.assertIsNone(classify_segment(SEGMENT_CEILING_CR + 1))
        self.assertIsNone(classify_segment(5001))


class TestSegmentsForFilter(unittest.TestCase):
    def test_nano_only(self) -> None:
        self.assertEqual(segments_for_filter("nano"), {"nano"})

    def test_micro_only(self) -> None:
        self.assertEqual(segments_for_filter("micro"), {"micro"})

    def test_default_nano_micro(self) -> None:
        self.assertEqual(segments_for_filter("nano_micro"), {"nano", "micro"})

    def test_all_segments(self) -> None:
        self.assertEqual(
            segments_for_filter("all"),
            {"nano", "micro", "small_micro", "extended_micro"},
        )

    def test_ideal_includes_preferred_universe(self) -> None:
        self.assertEqual(segments_for_filter("ideal"), {"nano", "micro", "small_micro"})

    def test_unknown_defaults_to_nano_micro(self) -> None:
        self.assertEqual(segments_for_filter("unknown"), {"nano", "micro"})


class TestUniverseBuilder(unittest.TestCase):
    def test_empty_build_does_not_claim_outputs_written(self) -> None:
        builder = UniverseBuilder.__new__(UniverseBuilder)
        builder.config = type(
            "ConfigStub",
            (),
            {"min_market_cap_cr": 100, "market_cap_limit_cr": 3500},
        )()
        builder.fetch_nse_equity_list = lambda stats: pd.DataFrame()
        builder.fetch_bse_scrip_map = lambda stats: pd.DataFrame()
        builder.fetch_nse_preopen_caps = lambda stats: pd.DataFrame()

        universe, stats = builder.build()

        self.assertTrue(universe.empty)
        self.assertFalse(stats.outputs_written)

    def test_includes_bse_only_symbols_with_bse_market_cap(self) -> None:
        builder = UniverseBuilder.__new__(UniverseBuilder)
        builder.config = type(
            "ConfigStub",
            (),
            {
                "min_market_cap_cr": 100,
                "market_cap_limit_cr": 3500,
                "universe_max_quote_lookups": 0,
                "bse_code_cache_path": "data/bse_code_cache.json",
            },
        )()
        builder._bse_cache = {}
        builder._save_bse_cache = lambda: None
        builder._prepare_nse_session = lambda: None
        builder.resolve_bse_code = lambda symbol, name: ""

        with patch.object(
            builder,
            "fetch_nse_equity_list",
            return_value=pd.DataFrame(
                [{"Symbol": "NSECO", "Name": "NSE Co", "Exchange": "NSE"}]
            ),
        ), patch.object(
            builder,
            "fetch_bse_scrip_map",
            return_value=pd.DataFrame(
                [
                    {
                        "Symbol": "BSEONLY",
                        "BSECode": "999999",
                        "BSE_Name": "BSE Only Co",
                        "BSE_MarketCap_Cr": 3200,
                    }
                ]
            ),
        ), patch.object(
            builder,
            "fetch_nse_preopen_caps",
            return_value=pd.DataFrame(),
        ):
            universe, _ = builder.build()

        row = universe[universe["Symbol"] == "BSEONLY"].iloc[0]
        self.assertEqual(row["Name"], "BSE Only Co")
        self.assertEqual(row["Exchange"], "BSE")
        self.assertEqual(row["BSECode"], "999999")
        self.assertEqual(row["MarketCap_Cr"], 3200)

    def test_bse_api_market_cap_field_is_supported(self) -> None:
        builder = UniverseBuilder.__new__(UniverseBuilder)
        builder.config = type("ConfigStub", (), {})()
        builder._bse_cache = {}
        builder.headers = {}
        stats = BuildStats()
        response = type(
            "ResponseStub",
            (),
            {
                "headers": {"content-type": "application/json"},
                "json": lambda self: [
                    {
                        "SCRIP_CD": "500002",
                        "Scrip_Name": "ABB India Ltd",
                        "scrip_id": "ABB",
                        "Mktcap": "157233.90",
                    }
                ],
            },
        )()
        builder._get = lambda url, **kwargs: response

        frame = builder.fetch_bse_scrip_map(stats)

        self.assertEqual(frame.iloc[0]["BSE_Name"], "ABB India Ltd")
        self.assertEqual(frame.iloc[0]["BSE_MarketCap_Cr"], 157233.90)

    def test_bse_sme_source_is_requested_and_labeled(self) -> None:
        builder = UniverseBuilder.__new__(UniverseBuilder)
        builder.headers = {}
        stats = BuildStats()
        calls: list[str] = []

        def get_response(url: str, **kwargs):
            calls.append(kwargs["params"]["segment"])
            return type(
                "ResponseStub",
                (),
                {
                    "headers": {"content-type": "application/json"},
                    "json": lambda self: [
                        {
                            "SCRIP_CD": "543210",
                            "Scrip_Name": "SME Co",
                            "scrip_id": "SMECO",
                            "Mktcap": "250",
                        }
                    ],
                },
            )()

        builder._get = get_response

        frame = builder.fetch_bse_scrip_map(stats)

        self.assertEqual(calls, ["Equity", "SME"])
        self.assertEqual(frame.iloc[0]["BSE_Platform"], "BSE Main Board+BSE SME")

    def test_common_listing_is_marked_nse_and_bse(self) -> None:
        builder = UniverseBuilder.__new__(UniverseBuilder)
        builder.config = type(
            "ConfigStub",
            (),
            {
                "min_market_cap_cr": 100,
                "market_cap_limit_cr": 3500,
                "universe_max_quote_lookups": 0,
                "bse_code_cache_path": "data/bse_code_cache.json",
            },
        )()
        builder._bse_cache = {}
        builder._save_bse_cache = lambda: None
        builder._prepare_nse_session = lambda: None
        builder.resolve_bse_code = lambda symbol, name: ""

        with patch.object(
            builder,
            "fetch_nse_equity_list",
            return_value=pd.DataFrame(
                [{"Symbol": "BOTH", "Name": "Both Co", "Exchange": "NSE"}]
            ),
        ), patch.object(
            builder,
            "fetch_bse_scrip_map",
            return_value=pd.DataFrame(
                [
                    {
                        "Symbol": "BOTH",
                        "BSECode": "500001",
                        "BSE_Name": "Both Co",
                        "BSE_MarketCap_Cr": 250,
                    }
                ]
            ),
        ), patch.object(
            builder,
            "fetch_nse_preopen_caps",
            return_value=pd.DataFrame(),
        ):
            universe, _ = builder.build()

        self.assertEqual(universe.iloc[0]["Exchange"], "NSE+BSE")


class TestCrawlerDocumentPriority(unittest.TestCase):
    def test_bse_announcement_variants_are_classified(self) -> None:
        self.assertEqual(
            classify_filing(
                "Announcement under Regulation 30 - Analyst / Investor Meet - Outcome",
                "Transcript of Analysts/Investor Earnings Conference Call for Q1/FY27",
            ),
            "concall_transcript",
        )
        self.assertEqual(
            classify_filing(
                "Un-Audited Standalone And Consolidated Results for the Quarter Ended",
                "Quarterly results",
            ),
            "financial_results",
        )
        self.assertEqual(
            classify_filing(
                "Announcement under Regulation 30 - Press Release / Media Release",
                "Binding term sheet worth approximately Rs. 1000 Crore",
            ),
            "strategic_update",
        )
        self.assertIsNone(classify_filing("Newspaper Publication", "Copy of newspaper"))

        self.assertEqual(
            classify_filing("Announcement under Regulation 30", "E2E_Q1_FY27_Transcript.pdf"),
            "concall_transcript",
        )

    def test_concall_is_prioritized_over_routine_document(self) -> None:
        make_filing = lambda document_type: Filing(
            exchange="BSE",
            symbol="TEST",
            filing_id=document_type,
            filed_at="2026-09-06",
            title=document_type,
            description="",
            document_type=document_type,
            url="https://example.com/file.pdf",
        )

        self.assertLess(
            CrawlerEngine.filing_priority(make_filing("concall_transcript")),
            CrawlerEngine.filing_priority(make_filing("annual_report")),
        )


if __name__ == "__main__":
    unittest.main()
