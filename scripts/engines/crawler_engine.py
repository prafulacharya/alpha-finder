"""Crawler Engine - Discovers and downloads filings from NSE/BSE exchanges."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from ..data_models import Filing
from ..utils import Config, CrawlerError
from ..utils.constants import (
    BSE_ANNOUNCEMENTS,
    BSE_ATTACHMENT,
    BSE_SEARCH,
    DOCUMENT_RULES,
    NSE_ANNOUNCEMENTS,
    classify_segment,
    segments_for_filter,
)


def classify_filing(title: str, description: str = "") -> str | None:
    """Classify filing type based on title and description."""
    haystack = f"{title} {description}".lower()
    for document_type, phrases in DOCUMENT_RULES:
        if any(phrase in haystack for phrase in phrases):
            return document_type
    return None


class CrawlerEngine:
    """Crawls NSE/BSE exchanges for corporate filings."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.transcript_dir = Path(config.transcript_dir)
        self.index_path = Path(config.filing_index_path)
        self.universe_path = Path(config.universe_path)
        
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self._bse_cache = self._load_bse_cache()

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
        path.write_text(
            json.dumps(self._bse_cache, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        """HTTP GET with retry logic."""
        last_error: Exception | None = None
        retries = int(kwargs.pop("_retries", 2))
        timeout = float(kwargs.pop("_timeout", 20))
        for attempt in range(retries):
            try:
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=timeout,
                    **kwargs
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
        raise CrawlerError(f"Request failed after retries: {url}") from last_error

    def load_universe(self) -> list[dict[str, Any]]:
        """Load micro-cap universe from CSV, filtered by segment and market cap."""
        if not self.universe_path.exists():
            raise CrawlerError(f"Universe file not found: {self.universe_path}")
        
        frame = pd.read_csv(self.universe_path)
        required = {"Symbol", "Name", "MarketCap_Cr"}
        missing = required.difference(frame.columns)
        if missing:
            raise CrawlerError(f"Universe missing columns: {', '.join(sorted(missing))}")
        
        frame["MarketCap_Cr"] = pd.to_numeric(frame["MarketCap_Cr"], errors="coerce")
        frame = frame[
            frame["MarketCap_Cr"].lt(self.config.market_cap_limit_cr)
            & frame["MarketCap_Cr"].gt(self.config.min_market_cap_cr)
        ]
        frame["Symbol"] = frame["Symbol"].astype(str).str.upper().str.strip()

        allowed_segments = segments_for_filter(self.config.crawl_segment)
        if "Segment" in frame.columns:
            frame = frame[frame["Segment"].isin(allowed_segments)]
        else:
            frame["_segment"] = frame["MarketCap_Cr"].apply(classify_segment)
            frame = frame[frame["_segment"].isin(allowed_segments)]
            frame.drop(columns=["_segment"], inplace=True)

        frame = frame.drop_duplicates(subset=["Symbol"])
        if self.config.symbols:
            frame = frame[frame["Symbol"].isin(self.config.symbols)]
        if self.config.max_companies is not None:
            frame = frame.head(self.config.max_companies)
        return frame.to_dict("records")

    @staticmethod
    def filing_priority(filing: Filing) -> tuple[int, str]:
        """Prioritize thesis-bearing documents over routine announcements."""
        priority = {
            "concall_transcript": 0,
            "financial_results": 1,
            "investor_presentation": 2,
            "annual_report": 3,
            "strategic_update": 4,
        }
        return priority.get(filing.document_type, 9), filing.filed_at

    def prepare_nse(self) -> None:
        """Prepare NSE session."""
        self.headers["Referer"] = (
            "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
        )
        try:
            self._get(self.headers["Referer"])
        except CrawlerError:
            pass

    def fetch_nse_filings(self, symbol: str, start: date, end: date) -> list[Filing]:
        """Fetch filings from NSE."""
        self.headers["Referer"] = (
            "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
        )
        filings: list[Filing] = []
        seen: set[str] = set()
        
        for index in ("equities", "sme"):
            response = self._get(
                NSE_ANNOUNCEMENTS,
                params={
                    "index": index,
                    "symbol": symbol,
                    "from_date": start.strftime("%d-%m-%Y"),
                    "to_date": end.strftime("%d-%m-%Y"),
                },
            )
            for item in response.json():
                title = str(item.get("attchmntText") or "")
                description = str(item.get("desc") or "")
                document_type = classify_filing(title, description)
                url = str(item.get("attchmntFile") or "")
                filing_id = str(item.get("seq_id") or url)
                
                if not document_type or not url.startswith("http") or filing_id in seen:
                    continue
                seen.add(filing_id)
                filings.append(
                    Filing(
                        exchange="NSE",
                        symbol=symbol,
                        filing_id=filing_id,
                        filed_at=str(item.get("an_dt") or item.get("sort_date") or ""),
                        title=title,
                        description=description,
                        document_type=document_type,
                        url=url,
                    )
                )
        return filings

    def resolve_bse_code(self, symbol: str, name: str) -> str:
        """Resolve BSE code for a symbol, using cache then search API."""
        cached = self._bse_cache.get(symbol.upper())
        if cached:
            return cached

        self.headers["Referer"] = "https://www.bseindia.com/"
        for query in (symbol, name):
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
        return ""

    def fetch_bse_filings(
        self, symbol: str, bse_code: str, start: date, end: date
    ) -> list[Filing]:
        """Fetch filings from BSE."""
        if not bse_code:
            return []
        
        self.headers["Referer"] = "https://www.bseindia.com/corporates/ann"
        filings: list[Filing] = []
        page = 1
        
        while True:
            response = self._get(
                BSE_ANNOUNCEMENTS,
                params={
                    "pageno": page,
                    "strCat": "-1",
                    "strPrevDate": start.strftime("%Y%m%d"),
                    "strScrip": bse_code,
                    "strSearch": "P",
                    "strToDate": end.strftime("%Y%m%d"),
                    "strType": "C",
                    "subcategory": "-1",
                },
            )
            payload = response.json()
            rows = payload.get("Table", []) if isinstance(payload, dict) else []
            
            for item in rows:
                title = str(item.get("NEWSSUB") or "")
                attachment = str(item.get("ATTACHMENTNAME") or "")
                description = " ".join(
                    str(item.get(key) or "")
                    for key in ("HEADLINE", "CATEGORYNAME", "SUBCATNAME")
                )
                document_type = classify_filing(
                    title,
                    f"{description} {attachment}",
                )
                
                if not document_type or not attachment:
                    continue
                filings.append(
                    Filing(
                        exchange="BSE",
                        symbol=symbol,
                        filing_id=str(item.get("NEWSID") or attachment),
                        filed_at=str(item.get("NEWS_DT") or item.get("DT_TM") or ""),
                        title=title,
                        description=description,
                        document_type=document_type,
                        url=f"{BSE_ATTACHMENT}/{attachment}",
                        bse_code=bse_code,
                    )
                )
            
            total = int((payload.get("Table1") or [{"ROWCNT": 0}])[0].get("ROWCNT", 0))
            if page * 50 >= total:
                break
            page += 1
        
        return filings

    @staticmethod
    def _safe(value: str) -> str:
        """Sanitize string for filenames."""
        return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_") or "unknown"

    def download_filing(self, filing: Filing) -> tuple[Path | None, str]:
        """Download and save a filing PDF."""
        urls = [filing.url]
        if filing.exchange == "BSE":
            attachment = filing.url.rsplit("/", 1)[-1]
            urls.append(f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{attachment}")
            filed_date = self._parse_bse_date(filing.filed_at)
            if filed_date:
                urls.append(
                    "https://www.bseindia.com/xml-data/corpfiling/CorpAttachment/"
                    f"{filed_date.year}/{filed_date.month}/{attachment}"
                )

        payload = b""
        errors = []
        for url in urls:
            try:
                response = self._get(url)
                if response.content.startswith(b"%PDF"):
                    payload = response.content
                    break
                errors.append(f"non-PDF: {url}")
            except Exception as exc:
                errors.append(f"{url}: {exc}")
        
        if not payload:
            if errors and all(item.startswith("non-PDF:") for item in errors):
                return None, "non_pdf_response"
            raise CrawlerError("; ".join(errors))
        
        digest = hashlib.sha256(payload).hexdigest()
        date_part = re.sub(r"\D", "", filing.filed_at)[:8] or "unknown"
        filename = (
            f"{self._safe(filing.symbol)}_{date_part}_{filing.document_type}_"
            f"{filing.exchange}_{digest[:10]}.pdf"
        )
        destination = self.transcript_dir / filename
        if not destination.exists():
            destination.write_bytes(payload)
            return destination, "downloaded"
        return destination, "already_present"

    @staticmethod
    def _parse_bse_date(value: str) -> date | None:
        """Parse BSE date format."""
        try:
            return datetime.fromisoformat(value).date()
        except (TypeError, ValueError):
            return None

    def load_index(self) -> dict[str, dict[str, Any]]:
        """Load filing index."""
        if not self.index_path.exists():
            return {}
        records = json.loads(self.index_path.read_text(encoding="utf-8"))
        return {f"{row['exchange']}:{row['filing_id']}": row for row in records}

    def write_index(self, records: dict[str, dict[str, Any]]) -> None:
        """Write filing index."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(
            records.values(),
            key=lambda row: (row.get("symbol", ""), row.get("filed_at", "")),
            reverse=True,
        )
        self.index_path.write_text(
            json.dumps(ordered, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def crawl(self) -> dict[str, int]:
        """Execute full crawl operation."""
        universe = self.load_universe()
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        index = self.load_index()
        
        end = date.today()
        start = end - timedelta(days=self.config.lookback_days - 1)
        
        stats = {
            "companies": len(universe),
            "discovered": 0,
            "relevant": 0,
            "downloaded": 0,
            "already_present": 0,
            "failed": 0,
        }

        if not self.config.bse_only:
            self.prepare_nse()
        for company in universe:
            symbol = str(company["Symbol"])
            name = str(company["Name"])
            bse_code = str(company.get("BSECode") or "").split(".")[0]
            
            if not bse_code or bse_code.lower() == "nan":
                try:
                    bse_code = self.resolve_bse_code(symbol, name)
                except Exception:
                    bse_code = ""

            filings: list[Filing] = []
            if not self.config.bse_only:
                try:
                    filings.extend(self.fetch_nse_filings(symbol, start, end))
                except CrawlerError:
                    stats["failed"] += 1
            
            try:
                filings.extend(self.fetch_bse_filings(symbol, bse_code, start, end))
            except CrawlerError:
                stats["failed"] += 1

            stats["discovered"] += len(filings)
            
            # Deduplicate filings
            unique: dict[str, Filing] = {}
            for filing in filings:
                dedupe_key = (
                    filing.document_type,
                    re.sub(r"\W+", "", filing.title.lower())[:180],
                    re.sub(r"\D", "", filing.filed_at)[:8],
                )
                unique.setdefault("|".join(dedupe_key), filing)
            
            selected = sorted(
                sorted(unique.values(), key=lambda f: f.filed_at, reverse=True),
                key=lambda f: self.filing_priority(f)[0],
            )[: self.config.max_documents_per_company]
            stats["relevant"] += len(selected)

            for filing in selected:
                key = f"{filing.exchange}:{filing.filing_id}"
                existing = index.get(key)
                if existing and existing.get("local_path"):
                    stats["already_present"] += 1
                    continue
                
                record = asdict(filing)
                record["crawled_at"] = datetime.now().astimezone().isoformat()
                try:
                    path, status = self.download_filing(filing)
                    record["status"] = status
                    record["local_path"] = str(path) if path else ""
                    stats[status] = stats.get(status, 0) + 1
                except Exception as exc:
                    record["status"] = "failed"
                    record["error"] = str(exc)
                    record["local_path"] = ""
                    stats["failed"] += 1
                index[key] = record
            
            self.write_index(index)
        
        self._save_bse_cache()
        return stats
