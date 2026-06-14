#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BEST_CHOICE_PATH = ROOT_DIR / "US_Best_Growth_Choice_2026-06-13.md"
UNDERFOLLOWED_PATH = ROOT_DIR / "US_Underfollowed_Growth_Stocks_2026-06-13.md"
HISTORY_PATH = ROOT_DIR / "US_Best_Growth_History.md"

HISTORY_HEADERS = [
    "Date",
    "Ticker",
    "Company",
    "Price",
    "Market Cap",
    "Selection",
    "Evidence Summary",
    "Price Change vs Previous Record",
    "Source",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def extract_table(markdown: str, heading: str) -> list[dict[str, str]]:
    lines = markdown.splitlines()
    heading_index = 0
    pattern = re.compile(rf"^##+\s+{re.escape(heading)}\s*$", re.I)
    for index, line in enumerate(lines):
        if pattern.match(line.strip()):
            heading_index = index + 1
            break

    table_lines: list[str] = []
    for line in lines[heading_index:]:
        if line.strip().startswith("|"):
            table_lines.append(line)
        elif table_lines:
            break

    if len(table_lines) < 2:
        return []
    headers = split_markdown_row(table_lines[0])
    rows = []
    for raw_line in table_lines[2:]:
        cells = split_markdown_row(raw_line)
        cells += [""] * max(0, len(headers) - len(cells))
        rows.append({headers[i]: cells[i] if i < len(cells) else "" for i in range(len(headers))})
    return rows


def table_rows_to_mapping(rows: list[dict[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in rows:
        key = row.get("Field", "").strip()
        if key:
            mapping[key] = row.get("Value", "").strip()
    return mapping


def normalize_ticker(value: str) -> str:
    match = re.search(r"`?([A-Z][A-Z0-9.]{0,9})`?", value or "")
    return match.group(1) if match else ""


def parse_price(value: str) -> float | None:
    clean = re.sub(r"[^0-9.]", "", value or "")
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def stock_market_snapshot(ticker: str) -> dict[str, str]:
    rows = extract_table(read_text(UNDERFOLLOWED_PATH), "Market Data Snapshot")
    for row in rows:
        if normalize_ticker(row.get("Ticker", "")) == ticker:
            return {"Price": row.get("Price", ""), "Market Cap": row.get("Market Cap", "")}
    return {"Price": "", "Market Cap": ""}


def existing_history_rows() -> list[dict[str, str]]:
    rows = extract_table(read_text(HISTORY_PATH), "Maintained Best Choice History")
    normalized = []
    for row in rows:
        normalized.append({header: row.get(header, "") for header in HISTORY_HEADERS})
    return normalized


def price_change_text(rows: list[dict[str, str]], ticker: str, current_date: str, current_price_text: str) -> str:
    current_price = parse_price(current_price_text)
    previous = [
        row
        for row in rows
        if normalize_ticker(row.get("Ticker", "")) == ticker and row.get("Date", "") < current_date and parse_price(row.get("Price", "")) is not None
    ]
    if current_price is None or not previous:
        return "baseline"
    prior = sorted(previous, key=lambda row: row.get("Date", ""))[-1]
    prior_price = parse_price(prior.get("Price", ""))
    if prior_price is None or prior_price == 0:
        return "baseline"
    pct = ((current_price / prior_price) - 1) * 100
    return f"{pct:+.1f}% since {prior.get('Date', '')}"


def build_history_row(record_date: str) -> dict[str, str]:
    best_text = read_text(BEST_CHOICE_PATH)
    decision = table_rows_to_mapping(extract_table(best_text, "Decision Snapshot"))
    evidence_rows = extract_table(best_text, "Evidence and Proof")
    ticker = normalize_ticker(decision.get("Ticker", ""))
    snapshot = stock_market_snapshot(ticker)
    evidence_summary = decision.get("Why Single Best") or decision.get("Thesis") or ""
    if evidence_rows:
        evidence_summary = f"{evidence_rows[0].get('Evidence', '')} {evidence_summary}".strip()
    rows = existing_history_rows()
    return {
        "Date": record_date,
        "Ticker": f"`{ticker}`" if ticker else "",
        "Company": decision.get("Company", ""),
        "Price": snapshot.get("Price", ""),
        "Market Cap": snapshot.get("Market Cap", ""),
        "Selection": decision.get("Selection", ""),
        "Evidence Summary": evidence_summary,
        "Price Change vs Previous Record": price_change_text(rows, ticker, record_date, snapshot.get("Price", "")),
        "Source": "[Best choice note](US_Best_Growth_Choice_2026-06-13.md)",
    }


def render_history(rows: list[dict[str, str]], updated_date: str) -> str:
    dedup: dict[str, dict[str, str]] = {row.get("Date", ""): row for row in rows if row.get("Date", "")}
    ordered = [dedup[key] for key in sorted(dedup)]
    lines = [
        "# Best Growth Choice History",
        "",
        f"Date: {updated_date}",
        "",
        "Use: Research watchlist history only. This is not personal financial advice or a buy/sell recommendation.",
        "",
        "## Maintained Best Choice History",
        "",
        "| " + " | ".join(HISTORY_HEADERS) + " |",
        "|---|---|---|---:|---:|---|---|---:|---|",
    ]
    for row in ordered:
        lines.append("| " + " | ".join(row.get(header, "") for header in HISTORY_HEADERS) + " |")
    lines.extend(
        [
            "",
            "## Maintenance Rule",
            "",
            "Append or update one row per refresh date after the single best huge-growth choice note is refreshed. Keep price and market-cap fields tied to the dated market-data snapshot, and use `Price Change vs Previous Record` to track the historical best pick over time.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Update LazyInvest best-choice history.")
    parser.add_argument("--date", default=date.today().isoformat(), help="record date in YYYY-MM-DD format")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        raise SystemExit("--date must be YYYY-MM-DD")
    rows = existing_history_rows()
    rows = [row for row in rows if row.get("Date") != args.date]
    rows.append(build_history_row(args.date))
    HISTORY_PATH.write_text(render_history(rows, args.date), encoding="utf-8")
    print(f"Updated {HISTORY_PATH.relative_to(ROOT_DIR)} for {args.date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
