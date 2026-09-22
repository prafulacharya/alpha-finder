"""Universe Builder - Fetches NSE/BSE equity lists and builds nano/micro cap universe."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from ..utils import Config
from ..utils.constants import (
    BSE_SCRIP_LIST_URL,
    BSE_SME_MARKET_PAGE,
    BSE_SEARCH,
    NSE_EQUITY_LIST_URL,
    NSE_HOME,
    NSE_PREOPEN_URL,
    NSE_QUOTE_URL,
    NSE_SME_EQUITY_LIST_URL,
    SEGMENT_CEILING_CR,
    classify_segment,
    segments_for_filter,
)

logger = logging.getLogger(__name__)


@dataclass
class BuildStats:
    """Summary of a universe build run."""

    nse_symbols: int = 0
    bse_symbols: int = 0
    with_market_cap: int = 0
    nano: int = 0
    micro: int = 0
    small_micro: int = 0
    sources_ok: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    outputs_written: bool = False


class UniverseBuilder:
    """Builds the investable universe from public NSE/BSE sources."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self._bse_cache: dict[str, str] = self._load_bse_cache()

    def _load_bse_cache(self) -> dict[str, str]:
        path = Path(self.config.bse_code_cache_path)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_bse_cache(self) -> None:
        path = Path(self.config.bse_code_cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._bse_cache, indent=2, sort_keys=True), encoding="utf-8")

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        retries = int(kwargs.pop("_retries", 3))
        timeout = float(kwargs.pop("_timeout", 20))
        for attempt in range(retries):
            try:
                response = self.session.get(
                    url, headers=self.headers, timeout=timeout, **kwargs
                )
                if response.status_code in {403, 429} and attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                if self.config.request_delay_seconds:
                    time.sleep(self.config.request_delay_seconds)
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise requests.RequestException(f"Request failed after retries: {url}") from last_error

    def _prepare_nse_session(self) -> None:
        self.headers["Referer"] = NSE_HOME
        try:
            self._get(NSE_HOME)
        except requests.RequestException:
            pass

    def fetch_nse_equity_list(self, stats: BuildStats) -> pd.DataFrame:
        """Fetch NSE main-board and SME equity symbol lists."""
        frames: list[pd.DataFrame] = []
        for url, label, platform in (
            (NSE_EQUITY_LIST_URL, "NSE EQUITY_L", "NSE Main Board"),
            (NSE_SME_EQUITY_LIST_URL, "NSE SME EQUITY_L", "NSE Emerge"),
        ):
            try:
                response = self._get(url)
                frame = pd.read_csv(StringIO(response.text))
                frame.columns = [str(c).strip() for c in frame.columns]
                symbol_col = next(
                    (c for c in frame.columns if c.upper() in {"SYMBOL", "SYMBOLS"}),
                    None,
                )
                name_col = next(
                    (c for c in frame.columns if "NAME" in c.upper()),
                    None,
                )
                if not symbol_col:
                    raise ValueError(f"No symbol column in {label}")
                out = pd.DataFrame(
                    {
                        "Symbol": frame[symbol_col].astype(str).str.upper().str.strip(),
                        "Name": frame[name_col].astype(str).str.strip()
                        if name_col
                        else frame[symbol_col].astype(str).str.strip(),
                        "Exchange": "NSE",
                        "Platform": platform,
                    }
                )
                frames.append(out)
                stats.sources_ok.append(label)
            except Exception as exc:
                stats.sources_failed.append(f"{label}: {exc}")
                logger.warning("Failed to fetch %s: %s", label, exc)

        if not frames:
            return pd.DataFrame(columns=["Symbol", "Name", "Exchange"])

        combined = pd.concat(frames, ignore_index=True).drop_duplicates(
            subset=["Symbol", "Platform"]
        )
        stats.nse_symbols = len(combined)
        return combined

    def fetch_bse_scrip_map(self, stats: BuildStats) -> pd.DataFrame:
        """Fetch BSE scrips and classify SME rows from the official SME page."""
        try:
            self.headers["Referer"] = "https://www.bseindia.com/"
            bse_sme_symbols = self.fetch_bse_sme_symbols(stats)
            records = []
            response = self._get(
                BSE_SCRIP_LIST_URL,
                params={
                    "Group": "",
                    "Scripcode": "",
                    "industry": "",
                    "segment": "Equity",
                    "status": "Active",
                },
            )
            if "json" not in response.headers.get("content-type", "").lower():
                raise ValueError(
                    f"BSE returned {response.headers.get('content-type', 'unknown')} "
                    "instead of JSON"
                )
            payload = response.json()
            rows = payload if isinstance(payload, list) else payload.get("Table", [])
            for row in rows:
                symbol = str(row.get("scrip_id") or row.get("SCRIP_ID") or "").upper().strip()
                name = str(
                    row.get("scrip_name")
                    or row.get("SCRIP_NAME")
                    or row.get("Scrip_Name")
                    or row.get("Issuer_Name")
                    or ""
                ).strip()
                code = str(row.get("scrip_cd") or row.get("SCRIP_CD") or "").strip()
                if symbol and code:
                    market_cap = _to_float(
                        row.get("market_cap")
                        or row.get("MARKET_CAP")
                        or row.get("marketCap")
                    )
                    bse_mktcap = _to_float(row.get("Mktcap"))
                    if bse_mktcap is not None:
                        # BSE ListofScripData reports Mktcap in INR crore.
                        market_cap = bse_mktcap
                    if market_cap and market_cap > 1_000_000:
                        market_cap /= 1e7
                    platform = (
                        "BSE Platform Unverified"
                        if bse_sme_symbols is None
                        else "BSE SME"
                        if symbol in bse_sme_symbols
                        else "BSE Main Board"
                    )
                    records.append(
                        {
                            "Symbol": symbol,
                            "BSECode": code,
                            "BSE_Name": name,
                            "BSE_MarketCap_Cr": market_cap,
                            "BSE_Platform": platform,
                        }
                    )
            frame = pd.DataFrame(records)
            if not frame.empty:
                frame = frame.drop_duplicates(subset=["Symbol"])
            stats.bse_symbols = len(frame)
            stats.sources_ok.append("BSE ListofScripData + BSE SME market page")
            return frame
        except Exception as exc:
            stats.sources_failed.append(f"BSE ListofScripData: {exc}")
            logger.warning("Failed to fetch BSE scrip list: %s", exc)
            return pd.DataFrame(columns=["Symbol", "BSECode", "BSE_Name", "BSE_Platform"])

    def fetch_bse_sme_symbols(self, stats: BuildStats) -> set[str] | None:
        """Fetch actively traded BSE SME symbols from the official SME market page."""
        try:
            response = self._get(BSE_SME_MARKET_PAGE, _timeout=30)
            tables = pd.read_html(StringIO(response.text))
            table = next((candidate for candidate in tables if candidate.shape[1] == 3), None)
            if table is None:
                raise ValueError("No BSE SME trading table found")
            symbols = {
                str(value).strip().upper()
                for value in table.iloc[:, 0]
                if pd.notna(value)
                and str(value).strip()
                and str(value).strip().upper() not in {"SECURITY NAME", "SYMBOL"}
            }
            if not symbols:
                raise ValueError("BSE SME trading table contained no symbols")
            stats.sources_ok.append("BSE SME market page")
            return symbols
        except Exception as exc:
            stats.sources_failed.append(f"BSE SME market page: {exc}")
            logger.warning("Failed to fetch BSE SME market page: %s", exc)
            return None

    def fetch_nse_preopen_caps(self, stats: BuildStats) -> pd.DataFrame:
        """Bulk market data from NSE pre-open API (price + volume)."""
        self._prepare_nse_session()
        self.headers["Referer"] = "https://www.nseindia.com/market-data/pre-open-market-cm-and-emerge-market"
        try:
            response = self._get(NSE_PREOPEN_URL, params={"key": "ALL"})
            payload = response.json()
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            records = []
            for item in rows:
                meta = item.get("metadata", item)
                symbol = str(meta.get("symbol") or meta.get("identifier", "")).upper().strip()
                if not symbol or symbol.startswith("NIFTY"):
                    continue
                last_price = _to_float(meta.get("lastPrice") or meta.get("pPrice"))
                volume = _to_float(meta.get("totalTradedVolume") or meta.get("tradedVolume"))
                traded_value = _to_float(meta.get("totalTradedValue") or meta.get("turnover"))
                avg_value_cr = traded_value / 1e7 if traded_value else None
                records.append(
                    {
                        "Symbol": symbol,
                        "LastPrice": last_price,
                        "Volume": volume,
                        "AvgDailyValue_Cr": avg_value_cr,
                    }
                )
            frame = pd.DataFrame(records)
            stats.sources_ok.append("NSE pre-open (bulk prices)")
            return frame
        except Exception as exc:
            stats.sources_failed.append(f"NSE pre-open: {exc}")
            logger.warning("NSE pre-open fetch failed: %s", exc)
            return pd.DataFrame(columns=["Symbol", "LastPrice", "Volume", "AvgDailyValue_Cr"])

    def fetch_nse_quote_cap(self, symbol: str) -> dict[str, Any]:
        """Fetch market cap for a single symbol via NSE quote API."""
        self.headers["Referer"] = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
        response = self._get(
            NSE_QUOTE_URL,
            params={"symbol": symbol},
            _retries=1,
            _timeout=8,
        )
        payload = response.json()
        info = payload.get("info", {}) or {}
        security = payload.get("securityInfo", {}) or {}
        price_info = payload.get("priceInfo", {}) or {}
        trade_info = payload.get("tradeInfo", {}) or {}

        last_price = _to_float(price_info.get("lastPrice"))
        issued = _to_float(security.get("issuedSize"))
        mcap_cr = _to_float(
            info.get("marketCap")
            or security.get("marketCap")
            or price_info.get("marketCap")
        )
        if mcap_cr and mcap_cr > 1_000_000:
            mcap_cr = mcap_cr / 1e7
        if not mcap_cr and last_price and issued:
            mcap_cr = last_price * issued / 1e7
        traded_value = _to_float(trade_info.get("totalTradedValue"))
        avg_value_cr = traded_value / 1e7 if traded_value else None
        name = str(info.get("companyName") or security.get("companyName") or symbol)

        return {
            "Symbol": symbol,
            "Name": name,
            "MarketCap_Cr": mcap_cr,
            "LastPrice": last_price,
            "AvgDailyValue_Cr": avg_value_cr,
        }

    def resolve_bse_code(self, symbol: str, name: str) -> str:
        """Resolve BSE scrip code, using cache then search API."""
        cached = self._bse_cache.get(symbol.upper())
        if cached:
            return cached

        self.headers["Referer"] = "https://www.bseindia.com/"
        for query in (symbol, name):
            if not query:
                continue
            try:
                response = self._get(BSE_SEARCH, params={"searchString": query})
                data = response.json()
                exact = [
                    row
                    for row in data
                    if str(row.get("shortName", "")).upper() == symbol.upper()
                    and "equity" in str(row.get("Type", "")).lower()
                ]
                if exact:
                    code = str(exact[0].get("strSricpCode") or "")
                    if code:
                        self._bse_cache[symbol.upper()] = code
                        return code
            except requests.RequestException:
                continue
        return ""

    def build(self) -> tuple[pd.DataFrame, BuildStats]:
        """Build full universe dataframe and statistics."""
        stats = BuildStats()
        ceiling = min(self.config.market_cap_limit_cr, SEGMENT_CEILING_CR)

        nse = self.fetch_nse_equity_list(stats)
        bse_map = self.fetch_bse_scrip_map(stats)
        # Index membership is optional enrichment and is not required to build
        # the exchange universe or calculate the market-cap filter.  The NSE
        # index endpoint is frequently unavailable for small-cap/SME indexes,
        # so avoid making the whole build depend on it.
        index_bulk = pd.DataFrame()
        stats.warnings.append("Skipped NSE index enrichment; using pre-open and quote data.")
        preopen = self.fetch_nse_preopen_caps(stats)

        if nse.empty and bse_map.empty:
            stats.warnings.append("No symbol master data retrieved from NSE or BSE.")
            return pd.DataFrame(), stats

        if nse.empty:
            universe = bse_map.rename(columns={"BSE_Name": "Name"}).copy()
            universe["Exchange"] = "BSE"
        else:
            universe = nse.copy()
            if not bse_map.empty:
                bse_columns = [
                    "Symbol",
                    "BSECode",
                    "BSE_Name",
                    "BSE_MarketCap_Cr",
                    "BSE_Platform",
                ]
                for column in bse_columns:
                    if column not in bse_map.columns:
                        bse_map[column] = None
                universe = universe.merge(bse_map[bse_columns], on="Symbol", how="outer")
                universe["Name"] = universe["Name"].fillna(universe["BSE_Name"])
                universe["Exchange"] = universe["Exchange"].fillna("BSE")
                universe["Exchange"] = universe.apply(
                    lambda row: (
                        "NSE+BSE"
                        if row.get("Exchange") == "NSE" and pd.notna(row.get("BSECode"))
                        else row.get("Exchange")
                    ),
                    axis=1,
                )

        if "BSE_Platform" in universe.columns:
            universe["Platform"] = universe.apply(
                lambda row: "+".join(
                    sorted(
                        {
                            str(value)
                            for value in (row.get("Platform"), row.get("BSE_Platform"))
                            if pd.notna(value) and str(value).strip()
                        }
                    )
                )
                or None,
                axis=1,
            )
            universe.drop(columns=["BSE_Platform"], inplace=True)

        platform_flags = {
            "BSE_Main_Board": "BSE Main Board",
            "BSE_SME": "BSE SME",
            "NSE_Main_Board": "NSE Main Board",
            "NSE_Emerge": "NSE Emerge",
        }
        platform_series = universe["Platform"] if "Platform" in universe else pd.Series(
            "", index=universe.index, dtype="object"
        )
        for column, platform in platform_flags.items():
            universe[column] = platform_series.fillna("").map(
                lambda value: platform in str(value).split("+")
            )

        if "BSE_MarketCap_Cr" in universe.columns:
            if "MarketCap_Cr" not in universe.columns:
                universe["MarketCap_Cr"] = None
            universe["MarketCap_Cr"] = universe["MarketCap_Cr"].fillna(
                universe["BSE_MarketCap_Cr"]
            )
            universe.drop(columns=["BSE_MarketCap_Cr"], inplace=True)
        if "BSE_Name" in universe.columns:
            universe["Name"] = universe["Name"].fillna(universe["BSE_Name"])
            universe.drop(columns=["BSE_Name"], inplace=True)

        for bulk in (index_bulk, preopen):
            if bulk.empty:
                continue
            merge_cols = [c for c in bulk.columns if c != "Symbol"]
            universe = universe.merge(bulk, on="Symbol", how="left", suffixes=("", "_dup"))
            for col in merge_cols:
                dup = f"{col}_dup"
                if dup in universe.columns:
                    universe[col] = universe[col].combine_first(universe[dup])
                    universe.drop(columns=[dup], inplace=True)

        # Fill missing market caps via individual NSE quotes (rate-limited)
        self._prepare_nse_session()
        mcap_values: dict[str, float | None] = {}
        quote_names: dict[str, str] = {}
        quote_avg: dict[str, float | None] = {}

        if "MarketCap_Cr" not in universe.columns:
            universe["MarketCap_Cr"] = None

        symbols_needing_quote = [
            sym
            for sym, cap in zip(universe["Symbol"], universe["MarketCap_Cr"], strict=False)
            if pd.isna(cap) or cap <= 0
        ]
        max_quotes = self.config.universe_max_quote_lookups
        quoted = 0
        consecutive_quote_failures = 0
        max_consecutive_quote_failures = 5
        for symbol in symbols_needing_quote:
            if quoted >= max_quotes:
                stats.warnings.append(
                    f"Stopped NSE quote lookups after {max_quotes} symbols "
                    "(raise universe_max_quote_lookups to fetch more)."
                )
                break
            try:
                quote = self.fetch_nse_quote_cap(symbol)
                mcap_values[symbol] = quote.get("MarketCap_Cr")
                quote_names[symbol] = quote.get("Name", symbol)
                if quote.get("AvgDailyValue_Cr") is not None:
                    quote_avg[symbol] = quote["AvgDailyValue_Cr"]
                quoted += 1
            except requests.RequestException:
                mcap_values[symbol] = None
                consecutive_quote_failures += 1
                if consecutive_quote_failures >= max_consecutive_quote_failures:
                    stats.warnings.append(
                        "Stopped NSE quote lookups after "
                        f"{max_consecutive_quote_failures} consecutive failures; "
                        "exchange quote API appears unavailable."
                    )
                    break
            else:
                consecutive_quote_failures = 0

        if mcap_values:
            universe["MarketCap_Cr"] = universe.apply(
                lambda row: mcap_values.get(row["Symbol"]) or row.get("MarketCap_Cr"),
                axis=1,
            )
            universe["Name"] = universe.apply(
                lambda row: quote_names.get(row["Symbol"], row["Name"]),
                axis=1,
            )
            if quote_avg:
                universe["AvgDailyValue_Cr"] = universe.apply(
                    lambda row: row.get("AvgDailyValue_Cr")
                    if pd.notna(row.get("AvgDailyValue_Cr"))
                    else quote_avg.get(row["Symbol"]),
                    axis=1,
                )

        universe["MarketCap_Cr"] = pd.to_numeric(universe.get("MarketCap_Cr"), errors="coerce")
        universe["Segment"] = universe["MarketCap_Cr"].apply(
            lambda v: classify_segment(v) if pd.notna(v) else None
        )
        universe = universe[
            universe["MarketCap_Cr"].lt(ceiling)
            & universe["MarketCap_Cr"].gt(self.config.min_market_cap_cr)
        ]
        universe = universe.drop_duplicates(subset=["Symbol"]).sort_values("MarketCap_Cr")

        # Back-fill BSE codes for rows still missing
        for idx, row in universe.iterrows():
            if pd.isna(row.get("BSECode")) or not str(row.get("BSECode")).strip():
                code = self.resolve_bse_code(str(row["Symbol"]), str(row["Name"]))
                if code:
                    universe.at[idx, "BSECode"] = code

        self._save_bse_cache()

        stats.with_market_cap = int(universe["MarketCap_Cr"].notna().sum())
        stats.nano = int((universe["Segment"] == "nano").sum())
        stats.micro = int((universe["Segment"] == "micro").sum())
        stats.small_micro = int((universe["Segment"] == "small_micro").sum())
        return universe, stats

    def write_outputs(self, universe: pd.DataFrame, crawl_segment: str) -> None:
        """Write parquet universe and sync backward-compatible micro_caps.csv."""
        parquet_path = Path(self.config.universe_parquet_path)
        csv_path = Path(self.config.universe_path)
        parquet_path.parent.mkdir(parents=True, exist_ok=True)

        columns = [
            "Symbol",
            "Name",
            "MarketCap_Cr",
            "Segment",
            "BSECode",
            "Exchange",
            "Platform",
            "BSE_Main_Board",
            "BSE_SME",
            "NSE_Main_Board",
            "NSE_Emerge",
            "AvgDailyValue_Cr",
            "MarketCapSource",
            "MarketCapAsOf",
        ]
        for col in columns:
            if col not in universe.columns:
                universe[col] = None
        # A provider response is a lead, not proof.  Persist source/date so the
        # analyst can independently reconcile price × latest outstanding shares.
        universe["MarketCapSource"] = universe["MarketCapSource"].fillna("NSE/BSE quote")
        universe["MarketCapAsOf"] = universe["MarketCapAsOf"].fillna(pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
        universe[columns].to_parquet(parquet_path, index=False)

        allowed = segments_for_filter(crawl_segment)
        sync = universe[universe["Segment"].isin(allowed)].copy()
        sync_csv = sync[["Symbol", "Name", "MarketCap_Cr"]].copy()
        if "BSECode" in sync.columns:
            sync_csv["BSECode"] = sync["BSECode"]
        if "Segment" in sync.columns:
            sync_csv["Segment"] = sync["Segment"]
        if "Exchange" in sync.columns:
            sync_csv["Exchange"] = sync["Exchange"]
        if "Platform" in sync.columns:
            sync_csv["Platform"] = sync["Platform"]
        for column in ("BSE_Main_Board", "BSE_SME", "NSE_Main_Board", "NSE_Emerge"):
            if column in sync.columns:
                sync_csv[column] = sync[column]
        sync_csv.to_csv(csv_path, index=False)

    def run(self, crawl_segment: str | None = None) -> BuildStats:
        """Build universe and persist outputs."""
        segment = crawl_segment or self.config.crawl_segment
        universe, stats = self.build()
        if universe.empty:
            stats.warnings.append("Universe is empty; outputs not written.")
            return stats
        self.write_outputs(universe, segment)
        stats.outputs_written = True
        return stats


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
