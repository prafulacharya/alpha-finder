# Alpha Finder Data Folders

## Required workflow data

The universe builder uses the official exchange masters: [NSE securities available for trading](https://www.nseindia.com/static/market-data/securities-available-for-trading) and [BSE list of securities](https://www.bseindia.com/corporates/list_scrips). TradingView's [all Indian stocks](https://in.tradingview.com/markets/stocks-india/market-movers-all-stocks/) page is useful as a cross-check, but is not used as the authoritative exchange universe or market-cap source.

- `universe/company_universe.csv`: the current NSE/BSE company universe used by the crawler and analysis engine. The default range is above INR 100 crore and below INR 3,500 crore.
- `documents/`: the single source folder for downloaded evidence PDFs. Keep `concalls/` for earnings-call transcripts and `filings/` for annual reports, financial results, order announcements, and capacity updates. The analysis engine reads PDFs recursively from this folder.
- `inputs/market_cap_audit.csv`: manually reconciled market-cap evidence. Copy the example and fill it when a market cap must be verified from price and shares outstanding.
- `inputs/valuation_scenarios.csv`: sourced forward EPS and valuation assumptions. Copy the example and fill it only when the company has enough evidence for a scenario.
- `filing_index.json`: crawler bookkeeping. It prevents the same filing from being downloaded repeatedly.

## Optional research aids

- `inputs/manual_sources.csv`: fallback URLs for documents that automatic NSE/BSE discovery misses. It is not required for every company.
- There are no required manual note folders. Generated per-company summaries are written to `output/company_memos/`.

## Generated outputs

- `output/ALPHA_MASTER_WATCHLIST.md`: human-readable research queue.
- `output/analysis_results.json`: machine-readable evidence, scores, coverage, and valuation results.
- `output/company_memos/<SYMBOL>.md`: one structured Screener-style memo per analyzed company.
- `universe/company_universe.parquet`: full structured universe output when the builder completes.

## Crawl schedule

- **Initial setup:** crawl the previous 365 days. This usually captures the latest annual report, four quarterly result cycles, investor presentations, strategic announcements, and available earnings-call transcripts.
- **Quarterly refresh:** run every 90-120 days with `--lookback-days 120`. `filing_index.json` prevents already-downloaded PDFs from being downloaded again.
- **Annual refresh:** once per year, run a 365-day crawl again to catch annual reports and late-uploaded documents.
- **Pilot before scale:** use `--symbols E2E,ABC` or `--max-companies 5` first. After checking the download quality, run the full universe.

Example commands:

```powershell
python -m scripts --crawl --symbols E2E --lookback-days 365
python -m scripts --crawl --symbols PSPPROJECT --bse-only --lookback-days 365
python -m scripts --crawl --lookback-days 120
python -m scripts --analyze-only
```

The crawler downloads original exchange PDFs only when the announcement metadata identifies a transcript, financial result, annual report, investor presentation, order, capacity, partnership, or other strategic update. It skips routine notices such as newspaper publications, ESOP grants, trading-window notices, and compliance certificates.
