#!/usr/bin/env python3
"""Collect a reproducible public-data bundle for LazyInvest daily reports."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "Mozilla/5.0 LazyInvest/1.0 contact@lazying.art"
FRED_SERIES = {
    "DGS2": "2-year Treasury constant maturity rate",
    "DGS10": "10-year Treasury constant maturity rate",
    "T10Y2Y": "10-year minus 2-year Treasury spread",
    "DFF": "Effective federal funds rate",
    "SOFR": "Secured overnight financing rate",
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    "UNRATE": "Unemployment rate",
    "PAYEMS": "All employees, total nonfarm",
    "INDPRO": "Industrial production index",
    "UMCSENT": "University of Michigan consumer sentiment",
}
MARKET_SYMBOLS = {
    "SPY": "S&P 500 ETF proxy",
    "QQQ": "Nasdaq-100 ETF proxy",
    "IWM": "Russell 2000 ETF proxy",
    "DIA": "Dow Jones ETF proxy",
    "XLK": "Technology sector ETF",
    "XLF": "Financials sector ETF",
    "XLI": "Industrials sector ETF",
    "XLE": "Energy sector ETF",
    "XLV": "Health care sector ETF",
    "XLY": "Consumer discretionary sector ETF",
    "XLP": "Consumer staples sector ETF",
    "XLU": "Utilities sector ETF",
    "XLC": "Communication services sector ETF",
    "XLRE": "Real estate sector ETF",
    "XLB": "Materials sector ETF",
}


def fetch_text(url: str, *, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str, *, timeout: int = 30) -> Any:
    return json.loads(fetch_text(url, timeout=timeout))


def newest_observations(series_id: str, limit: int = 6) -> list[dict[str, str]]:
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv?"
        + urllib.parse.urlencode({"id": series_id})
    )
    text = fetch_text(url)
    rows = list(csv.DictReader(io.StringIO(text)))
    value_rows = [
        {
            "date": row.get("DATE", row.get("observation_date", "")),
            "value": row.get(series_id, ""),
        }
        for row in rows
        if row.get(series_id) not in {"", "."}
    ]
    return value_rows[-limit:]


def yahoo_chart_quote(symbol: str) -> dict[str, Any]:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(symbol)
        + "?"
        + urllib.parse.urlencode({"range": "7d", "interval": "1d"})
    )
    data = fetch_json(url)
    result = data.get("chart", {}).get("result", [{}])[0]
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    meta = result.get("meta", {})
    close_values = quote.get("close", [])
    selected_index = None
    for index in range(len(close_values) - 1, -1, -1):
        if close_values[index] is not None:
            selected_index = index
            break
    if selected_index is None:
        raise ValueError(f"no close value returned for {symbol}")
    ts = timestamps[selected_index] if selected_index < len(timestamps) else None
    date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else ""

    def value(name: str) -> Any:
        values = quote.get(name, [])
        return values[selected_index] if selected_index < len(values) else None

    return {
        "symbol": symbol,
        "description": MARKET_SYMBOLS.get(symbol, ""),
        "provider": "Yahoo Finance chart endpoint",
        "source_url": url,
        "date": date,
        "currency": meta.get("currency"),
        "exchange": meta.get("exchangeName"),
        "regular_market_time": meta.get("regularMarketTime"),
        "previous_close": meta.get("chartPreviousClose"),
        "open": value("open"),
        "high": value("high"),
        "low": value("low"),
        "close": value("close"),
        "volume": value("volume"),
    }


def extract_maintained_tickers(path: Path, max_tickers: int) -> list[str]:
    text = path.read_text(encoding="utf-8")
    section = text
    marker = "## Maintained Stock Table"
    if marker in text:
        section = text.split(marker, 1)[1]
        next_heading = re.search(r"\n##\s+", section)
        if next_heading:
            section = section[: next_heading.start()]

    tickers: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0].lower() == "ticker":
            continue
        match = re.search(r"`([A-Z][A-Z0-9.-]{0,7})`", cells[0])
        if not match:
            match = re.search(r"\b([A-Z][A-Z0-9.-]{0,7})\b", cells[0])
        if match:
            ticker = match.group(1).replace(".", "-")
            if ticker not in tickers:
                tickers.append(ticker)
        if len(tickers) >= max_tickers:
            break
    return tickers


def cik_lookup() -> dict[str, dict[str, Any]]:
    data = fetch_json("https://www.sec.gov/files/company_tickers.json")
    lookup: dict[str, dict[str, Any]] = {}
    for item in data.values():
        ticker = str(item.get("ticker", "")).upper().replace(".", "-")
        if ticker:
            cik = str(item.get("cik_str", "")).zfill(10)
            lookup[ticker] = {
                "cik": cik,
                "title": item.get("title", ""),
                "ticker": item.get("ticker", ""),
            }
    return lookup


def recent_sec_filings(ticker: str, cik: str, limit: int = 8) -> dict[str, Any]:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        data = fetch_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return recent_sec_filings_atom(ticker, cik, limit=limit, api_error=str(exc))

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])
    filings = []
    for form, filing_date, accession, primary_doc in zip(
        forms, dates, accession_numbers, primary_documents
    ):
        accession_clean = str(accession).replace("-", "")
        archive_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{primary_doc}"
            if primary_doc
            else ""
        )
        filings.append(
            {
                "form": form,
                "filing_date": filing_date,
                "accession_number": accession,
                "document_url": archive_url,
            }
        )
        if len(filings) >= limit:
            break
    return {
        "ticker": ticker,
        "cik": cik,
        "company_name": data.get("name"),
        "source_url": url,
        "recent_filings": filings,
    }


def recent_sec_filings_atom(
    ticker: str, cik: str, *, limit: int = 8, api_error: str = ""
) -> dict[str, Any]:
    url = (
        "https://www.sec.gov/cgi-bin/browse-edgar?"
        + urllib.parse.urlencode(
            {
                "action": "getcompany",
                "CIK": ticker,
                "owner": "include",
                "count": str(limit),
                "output": "atom",
            }
        )
    )
    try:
        text = fetch_text(url)
        root = ET.fromstring(text)
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
        return {
            "ticker": ticker,
            "cik": cik,
            "source_url": url,
            "error": str(exc),
            "submissions_api_error": api_error,
        }

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    filings = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        updated = (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip()
        link = entry.find("atom:link", ns)
        href = link.get("href", "") if link is not None else ""
        form = title.split(" - ", 1)[0].strip()
        filings.append(
            {
                "form": form,
                "filing_date": updated[:10],
                "title": title,
                "document_url": href,
            }
        )
        if len(filings) >= limit:
            break
    return {
        "ticker": ticker,
        "cik": cik,
        "source_url": url,
        "recent_filings": filings,
        "submissions_api_error": api_error,
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    tickers = extract_maintained_tickers(args.stock_table, args.max_tickers)
    snapshot: dict[str, Any] = {
        "research_date": args.date,
        "collected_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "disclaimer": "Research watchlist support data only; not personal financial advice.",
        "inputs": {
            "stock_table": str(args.stock_table),
            "source_policy": "Use primary and reputable public data; refresh before investment decisions.",
        },
        "maintained_tickers": tickers,
        "market_quotes": [],
        "macro_fred": {},
        "sec_recent_filings": {},
        "source_links": {
            "fred": "https://fred.stlouisfed.org/",
            "yahoo_chart_api": "https://query1.finance.yahoo.com/v8/finance/chart/",
            "sec_company_tickers": "https://www.sec.gov/files/company_tickers.json",
            "sec_submissions_api": "https://data.sec.gov/submissions/",
            "sec_atom_feed": "https://www.sec.gov/cgi-bin/browse-edgar",
        },
        "errors": [],
    }

    for symbol in MARKET_SYMBOLS:
        try:
            snapshot["market_quotes"].append(yahoo_chart_quote(symbol))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            snapshot["errors"].append({"source": "yahoo_chart", "symbol": symbol, "error": str(exc)})

    for series_id, description in FRED_SERIES.items():
        try:
            snapshot["macro_fred"][series_id] = {
                "description": description,
                "observations": newest_observations(series_id),
                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            }
        except (urllib.error.URLError, TimeoutError, csv.Error) as exc:
            snapshot["errors"].append({"source": "fred", "series": series_id, "error": str(exc)})

    try:
        lookup = cik_lookup()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        lookup = {}
        snapshot["errors"].append({"source": "sec_company_tickers", "error": str(exc)})

    for ticker in tickers:
        company = lookup.get(ticker)
        if not company:
            snapshot["errors"].append({"source": "sec_lookup", "ticker": ticker, "error": "no CIK match"})
            continue
        snapshot["sec_recent_filings"][ticker] = recent_sec_filings(ticker, company["cik"])
        time.sleep(args.sec_pause_seconds)

    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Research date in YYYY-MM-DD form")
    parser.add_argument("--stock-table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tickers", type=int, default=40)
    parser.add_argument("--sec-pause-seconds", type=float, default=0.15)
    args = parser.parse_args()

    if not args.stock_table.exists():
        print(f"stock table not found: {args.stock_table}", file=sys.stderr)
        return 2

    snapshot = collect(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
