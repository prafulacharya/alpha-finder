"""Discover fresh NSE/NSE-SME filing-led alpha candidates.

This is a fast first-pass scanner. It intentionally excludes symbols already
present in the local watchlist/universe and ranks new names by recent exchange
announcements that hint at order wins, capacity, results, presentations, or
strategic activity.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT_JSON = DATA / "new_alpha_candidates.json"
OUT_CSV = DATA / "new_alpha_candidates.csv"
OUT_MD = ROOT / "NEW_ALPHA_CANDIDATES.md"

NSE_HOME = "https://www.nseindia.com/"
NSE_ANNOUNCEMENTS = "https://www.nseindia.com/api/corporate-announcements"

NOISE = re.compile(
    r"takeover regulations|regulation 31|regulation 29|regulation 30\(11\)|"
    r"spurt in volume|trading window|newspaper publication|loss of share certificate|"
    r"certificate under|reconciliation of share capital|investor complaint|"
    r"compliance certificate|disclosure under sebi takeover",
    re.I,
)

SIGNALS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    (
        "main-board migration",
        re.compile(
            r"\bmain board\b.{0,50}\b(?:migration|transfer|listing)\b|"
            r"\bsme.{0,30}main board\b|"
            r"\bin-principle approval\b",
            re.I,
        ),
        15,
    ),
    (
        "migration in progress",
        re.compile(r"\bpostal ballot\b.{0,50}\b(?:migration|mainboard)\b", re.I),
        10,
    ),
    ("order win", re.compile(r"order|contract|letter of award|letter of acceptance|work order|purchase order", re.I), 10),
    ("capacity/production", re.compile(r"capacity|expansion|commission|commercial production|new plant|facility", re.I), 8),
    ("strategic action", re.compile(r"acquisition|joint venture|strategic alliance|mou|memorandum of understanding", re.I), 6),
    ("investor presentation", re.compile(r"investor presentation|corporate presentation", re.I), 5),
    ("financial results", re.compile(r"financial results|audited results|unaudited results", re.I), 4),
    ("credit rating", re.compile(r"credit rating|rating", re.I), 2),
)


def headers(referer: str = NSE_HOME) -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
    }


def known_symbols() -> set[str]:
    symbols: set[str] = set()
    for path in (ROOT / "ALPHA_MASTER_WATCHLIST.md", DATA / "micro_caps.csv"):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        symbols.update(re.findall(r"\*\*([A-Z0-9-]+)\*\*", text))
        if path.suffix == ".csv":
            for line in text.splitlines()[1:]:
                if line.strip():
                    symbols.add(line.split(",", 1)[0].strip().upper())
    return symbols


def fetch_announcements(days: int) -> list[dict[str, Any]]:
    session = requests.Session()
    session.get(NSE_HOME, headers=headers(), timeout=30)
    start = (date.today() - timedelta(days=days)).strftime("%d-%m-%Y")
    end = date.today().strftime("%d-%m-%Y")
    rows: list[dict[str, Any]] = []
    for index in ("equities", "sme"):
        response = session.get(
            NSE_ANNOUNCEMENTS,
            headers=headers(
                "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
            ),
            params={"index": index, "from_date": start, "to_date": end},
            timeout=60,
        )
        response.raise_for_status()
        for item in response.json():
            item["_segment"] = index
            rows.append(item)
        time.sleep(0.2)
    return rows


def score_rows(rows: list[dict[str, Any]], old_symbols: set[str]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "symbol": "",
            "name": "",
            "segment": "",
            "industry": "",
            "isin": "",
            "score": 0,
            "filing_count": 0,
            "dates": set(),
            "signals": set(),
            "filings": [],
        }
    )
    for item in rows:
        symbol = str(item.get("symbol") or "").upper().strip()
        if not symbol or symbol in old_symbols:
            continue
        haystack = " ".join(
            str(item.get(key) or "")
            for key in ("attchmntText", "desc", "sm_name", "smIndustry")
        )
        if NOISE.search(haystack):
            continue
        hits = [(label, points) for label, pattern, points in SIGNALS if pattern.search(haystack)]
        if not hits:
            continue

        record = candidates[symbol]
        record["symbol"] = symbol
        record["name"] = str(item.get("sm_name") or symbol)
        record["segment"] = str(item.get("_segment") or "")
        record["industry"] = str(item.get("smIndustry") or "")
        record["isin"] = str(item.get("sm_isin") or "")
        record["score"] += sum(points for _, points in hits)
        record["filing_count"] += 1
        record["dates"].add(str(item.get("an_dt") or "")[:11])
        record["signals"].update(label for label, _ in hits)
        if len(record["filings"]) < 5:
            record["filings"].append(
                {
                    "date": item.get("an_dt"),
                    "desc": item.get("desc"),
                    "title": item.get("attchmntText"),
                    "url": item.get("attchmntFile"),
                    "signals": [label for label, _ in hits],
                }
            )

    ranked = sorted(
        candidates.values(),
        key=lambda row: (
            row["segment"] == "sme",
            row["score"],
            row["filing_count"],
            len(row["dates"]),
        ),
        reverse=True,
    )
    for row in ranked:
        row["dates"] = sorted(row["dates"])
        row["signals"] = sorted(row["signals"])
    return ranked


def write_outputs(candidates: list[dict[str, Any]], days: int, fetched: int) -> None:
    DATA.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Symbol", "Name", "Segment", "Score", "Filings", "Dates", "Signals", "Top Filing", "URL"])
        for row in candidates:
            top = row["filings"][0] if row["filings"] else {}
            writer.writerow(
                [
                    row["symbol"],
                    row["name"],
                    row["segment"],
                    row["score"],
                    row["filing_count"],
                    "; ".join(row["dates"]),
                    ", ".join(row["signals"]),
                    top.get("title"),
                    top.get("url"),
                ]
            )

    lines = [
        "# New Alpha Candidates",
        "",
        f"Generated: {date.today().isoformat()}",
        f"Lookback: last {days} days of NSE/NSE-SME announcements",
        f"Exchange rows scanned: {fetched:,}",
        "",
        "> Fresh-name discovery only. Existing watchlist/universe symbols were excluded. "
        "Market cap, liquidity, valuation, governance, and price run-up are not verified here.",
        "",
        "| Symbol | Segment | Score | Filings | Signals | Why It Surfaced |",
        "| :--- | :--- | ---: | ---: | :--- | :--- |",
    ]
    for row in candidates[:40]:
        top = row["filings"][0] if row["filings"] else {}
        title = str(top.get("title") or "").replace("|", "\\|")
        lines.append(
            f"| **{row['symbol']}** | {row['segment']} | {row['score']} | "
            f"{row['filing_count']} | {', '.join(row['signals'])} | {title} |"
        )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    days = int(argv[0]) if argv else 30
    rows = fetch_announcements(days)
    candidates = score_rows(rows, known_symbols())
    write_outputs(candidates, days, len(rows))
    print(f"Scanned {len(rows):,} exchange rows; wrote {len(candidates)} fresh candidates.")
    print(f"Report: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
