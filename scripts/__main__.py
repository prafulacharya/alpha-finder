"""CLI entry point for Alpha Finder."""

import argparse
import sys

from .engines.universe_builder import UniverseBuilder
from .orchestrator import ResearchOrchestrator
from .utils import Config


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Alpha Finder - Evidence-first research prioritization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Data files:\n"
            "  data/universe.parquet   Full universe (<= market-cap ceiling)\n"
            "  data/universe/company_universe.csv  Crawler-compatible NSE/BSE subset\n"
            "  data/inputs/manual_sources.csv      Optional manual PDF URLs.\n"
            "                          Add direct exchange/company links here; automatic\n"
            "                          discovery uses --crawl against micro_caps.csv.\n"
        ),
    )
    parser.add_argument(
        "--build-universe",
        action="store_true",
        help=(
            "Fetch NSE/BSE equity lists and market caps, classify nano/micro/small_micro "
            "segments, write data/universe.parquet and sync data/micro_caps.csv"
        ),
    )
    parser.add_argument(
        "--crawl",
        action="store_true",
        help="Run full pipeline with web crawling",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Purge old data before crawling (find undiscovered alpha)",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Analyze existing documents without crawling",
    )
    parser.add_argument(
        "--min-market-cap",
        type=float,
        default=100,
        help="Minimum market cap in crores (default: 100; stocks must be above this)",
    )
    parser.add_argument(
        "--market-cap-limit",
        type=float,
        default=3500,
        help="Market-cap ceiling in crores (default: 3500; stocks must be below this)",
    )
    parser.add_argument(
        "--segment",
        choices=["nano", "micro", "nano_micro", "ideal", "all"],
        default="all",
        help=(
            "Universe segment filter for crawl and micro_caps.csv sync "
            "(default: all = every company below the active market-cap ceiling; "
            "ideal = preferred focus <=1000 Cr). "
            "Builder stores all segments up to --market-cap-limit."
        ),
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=365,
        help="Days to look back for the initial backfill (default: 365; quarterly refresh: 120)",
    )
    parser.add_argument(
        "--max-companies",
        type=int,
        help="Limit crawl/analyze to the first N universe companies (useful for a pilot)",
    )
    parser.add_argument(
        "--symbols",
        help="Comma-separated symbols to crawl/analyze instead of the full universe",
    )
    parser.add_argument(
        "--bse-only",
        action="store_true",
        help="Use BSE announcements without waiting for NSE (useful when NSE is unavailable)",
    )

    args = parser.parse_args()

    try:
        config = Config(
            min_market_cap_cr=args.min_market_cap,
            market_cap_limit_cr=args.market_cap_limit,
            lookback_days=args.lookback_days,
            crawl_segment=args.segment,
            max_companies=args.max_companies,
            symbols=tuple(
                symbol.strip().upper()
                for symbol in (args.symbols or "").split(",")
                if symbol.strip()
            ),
            bse_only=args.bse_only,
        )
        orchestrator = ResearchOrchestrator(config)

        if args.build_universe:
            print("Building universe from NSE/BSE public APIs...")
            builder = UniverseBuilder(config)
            stats = builder.run(crawl_segment=args.segment)
            print(f"  NSE symbols loaded: {stats.nse_symbols}")
            print(f"  BSE symbols loaded: {stats.bse_symbols}")
            print(f"  With market cap:    {stats.with_market_cap}")
            print(f"  nano (<100 Cr):     {stats.nano}")
            print(f"  micro (100-500 Cr): {stats.micro}")
            print(f"  small_micro (500-1000 Cr): {stats.small_micro}")
            if stats.sources_ok:
                print(f"  Sources OK: {', '.join(stats.sources_ok)}")
            if stats.sources_failed:
                print(f"  Sources failed: {', '.join(stats.sources_failed)}")
            if stats.warnings:
                for warning in stats.warnings:
                    print(f"  Warning: {warning}")
            if stats.outputs_written:
                print(f"\nUniverse written to {config.universe_parquet_path}")
                print(f"Crawler CSV synced to {config.universe_path}")
            else:
                print("\nUniverse was not written because no market-cap-qualified rows were available.")
            if not (args.crawl or args.fresh or args.analyze_only):
                return 0 if stats.outputs_written else 1

        if args.crawl or args.fresh:
            if args.fresh:
                print("Starting fresh discovery (purging old data)...")
            else:
                print("Starting full pipeline (crawl + analyze)...")
            results = orchestrator.run_full_pipeline(purge=args.fresh)
        elif args.analyze_only:
            print("Starting analysis on existing documents...")
            results = orchestrator.run_analysis_only()
        elif not args.build_universe:
            parser.print_help()
            return 1
        else:
            return 0

        print(f"\nPipeline complete. Results written to {config.output_json}")
        print(f"Report: {config.output_report}")
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted. No partial universe output was written.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
