#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
CHAT_DIR = DATA_DIR / "chat"
JOB_DIR = DATA_DIR / "jobs"
SETTINGS_PATH = DATA_DIR / "settings.json"
CHAT_PROMPT_PATH = ROOT_DIR / "prompts" / "lazyinvest-chat.md"
RESEARCH_PROMPT_PATH = ROOT_DIR / "prompts" / "lazyinvest-research-agent.md"
DEFAULT_MATRIX = ROOT_DIR / "US_Sector_Investment_Matrix_2026-06-13.md"
DEFAULT_TIMEOUT_SECONDS = 180
RESEARCH_TIMEOUT_SECONDS = 60 * 45
DEFAULT_STOCK_TABLE = ROOT_DIR / "US_Stock_Research_Table_2026-06-13.md"


DEFAULT_SETTINGS: dict[str, Any] = {
    "profiles": {
        "chat": {"model": "gpt-5.5", "reasoning": "medium"},
        "research": {"model": "gpt-5.5", "reasoning": "xhigh"},
        "agent": {"model": "gpt-5.5", "reasoning": "xhigh"},
    },
    "table": {
        "source": "US_Sector_Investment_Matrix_2026-06-13.md",
        "heading": "Maintained Sector Table",
    },
    "stock_table": {
        "source": "US_Stock_Research_Table_2026-06-13.md",
        "heading": "Maintained Stock Table",
    },
}

REASONING_LEVELS = {"low", "medium", "high", "xhigh"}
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ensure_dirs() -> None:
    for path in (DATA_DIR, CHAT_DIR, JOB_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def safe_token(value: str, fallback: str = "item") -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip("-")
    return token or fallback


def load_settings() -> dict[str, Any]:
    settings = read_json(SETTINGS_PATH, DEFAULT_SETTINGS)
    if not isinstance(settings, dict):
        settings = dict(DEFAULT_SETTINGS)
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    merged.update({k: v for k, v in settings.items() if k != "profiles"})
    profiles = dict(DEFAULT_SETTINGS["profiles"])
    for name, profile in dict(settings.get("profiles") or {}).items():
        if isinstance(profile, dict):
            profiles[name] = {
                "model": str(profile.get("model") or profiles.get(name, profiles["chat"])["model"]),
                "reasoning": str(profile.get("reasoning") or profiles.get(name, profiles["chat"])["reasoning"]),
            }
    merged["profiles"] = profiles
    return merged


def sanitize_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    incoming_profiles = payload.get("profiles") if isinstance(payload, dict) else {}
    profiles = dict(current["profiles"])
    if isinstance(incoming_profiles, dict):
        for name in ("chat", "research", "agent"):
            profile = incoming_profiles.get(name)
            if not isinstance(profile, dict):
                continue
            model = str(profile.get("model") or profiles[name]["model"]).strip()
            reasoning = str(profile.get("reasoning") or profiles[name]["reasoning"]).strip()
            if not MODEL_PATTERN.fullmatch(model):
                raise ValueError(f"Invalid model for {name}")
            if reasoning not in REASONING_LEVELS:
                raise ValueError(f"Invalid reasoning for {name}")
            profiles[name] = {"model": model, "reasoning": reasoning}
    current["profiles"] = profiles
    return current


def profile(name: str) -> dict[str, str]:
    settings = load_settings()
    selected = settings["profiles"].get(name) or settings["profiles"]["chat"]
    return {"model": str(selected["model"]), "reasoning": str(selected["reasoning"])}


def configured_repo_path(section: str, default_path: Path) -> Path:
    settings = load_settings()
    source = str((settings.get(section) or {}).get("source") or default_path.name)
    candidate = (ROOT_DIR / source).resolve()
    if ROOT_DIR.resolve() not in candidate.parents and candidate != ROOT_DIR.resolve():
        return default_path
    return candidate


def matrix_path() -> Path:
    return configured_repo_path("table", DEFAULT_MATRIX)


def stock_table_path() -> Path:
    return configured_repo_path("stock_table", DEFAULT_STOCK_TABLE)


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def extract_table(markdown: str, heading: str = "Maintained Sector Table") -> dict[str, Any]:
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
        return {"headers": [], "rows": [], "raw": [], "updated_at": now_iso()}

    headers = split_markdown_row(table_lines[0])
    rows = []
    for raw_line in table_lines[2:]:
        cells = split_markdown_row(raw_line)
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        rows.append({headers[i]: cells[i] if i < len(cells) else "" for i in range(len(headers))})
    return {
        "headers": headers,
        "rows": rows,
        "raw": table_lines,
        "updated_at": now_iso(),
    }


def markdown_table_snapshot(path: Path, heading: str) -> dict[str, Any]:
    text = read_text(path)
    table = extract_table(text, heading=heading)
    table["source"] = str(path.relative_to(ROOT_DIR))
    try:
        stat = path.stat()
        table["mtime"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        table["size"] = stat.st_size
    except FileNotFoundError:
        table["mtime"] = ""
        table["size"] = 0
    return table


def table_snapshot() -> dict[str, Any]:
    settings = load_settings()
    heading = str((settings.get("table") or {}).get("heading") or "Maintained Sector Table")
    return markdown_table_snapshot(matrix_path(), heading)


def stock_table_snapshot() -> dict[str, Any]:
    settings = load_settings()
    heading = str((settings.get("stock_table") or {}).get("heading") or "Maintained Stock Table")
    return markdown_table_snapshot(stock_table_path(), heading)


def normalize_ticker(value: str) -> str:
    match = re.search(r"`?([A-Z][A-Z0-9.]{0,9})`?", value or "")
    return match.group(1) if match else ""


def strip_markdown(value: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", value)
    text = text.replace("`", "")
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_watchlist_sections() -> dict[str, dict[str, str]]:
    text = read_text(ROOT_DIR / "US_Underfollowed_Growth_Stocks_2026-06-13.md")
    lines = text.splitlines()
    sections: dict[str, dict[str, str]] = {}
    heading_re = re.compile(r"^###\s+`([^`]+)`\s+-\s+(.+?)\s*$")
    for index, line in enumerate(lines):
        match = heading_re.match(line)
        if not match:
            continue
        ticker, company = match.group(1), match.group(2)
        body: list[str] = []
        for next_line in lines[index + 1 :]:
            if re.match(r"^##+\s+", next_line):
                break
            body.append(next_line)
        sections[ticker] = {"ticker": ticker, "company": company, "analysis": strip_markdown("\n".join(body))}
    return sections


def extract_sector_ticker_notes() -> dict[str, list[str]]:
    notes: dict[str, list[str]] = {}
    text = read_text(matrix_path())
    bullet_re = re.compile(r"^-\s+((?:`[A-Z][A-Z0-9.]{0,9}`(?:,\s*)?)+):\s+(.+)$")
    for line in text.splitlines():
        match = bullet_re.match(line.strip())
        if not match:
            continue
        tickers = re.findall(r"`([A-Z][A-Z0-9.]{0,9})`", match.group(1))
        note = strip_markdown(match.group(2))
        for ticker in tickers:
            notes.setdefault(ticker, []).append(note)
    return notes


def stock_details_snapshot() -> dict[str, Any]:
    stock_table = stock_table_snapshot()
    details: dict[str, dict[str, Any]] = {}
    for row in stock_table.get("rows", []):
        ticker = normalize_ticker(str(row.get("Ticker") or ""))
        if not ticker:
            continue
        details[ticker] = {
            "ticker": ticker,
            "company": row.get("Company", ""),
            "category": row.get("Category", ""),
            "bucket": row.get("Bucket", ""),
            "why": row.get("Why It Matters", ""),
            "evidence": row.get("Evidence Snapshot", ""),
            "risks": row.get("Main Risks", ""),
            "monitor": row.get("Monitor", ""),
            "source": row.get("Source", ""),
            "row": row,
        }

    watchlist = extract_watchlist_sections()
    for ticker, section in watchlist.items():
        item = details.setdefault(ticker, {"ticker": ticker, "row": {}})
        item.setdefault("company", section.get("company", ""))
        if not item.get("company"):
            item["company"] = section.get("company", "")
        item["analysis"] = section.get("analysis", "")

    sector_notes = extract_sector_ticker_notes()
    for ticker, notes in sector_notes.items():
        item = details.setdefault(ticker, {"ticker": ticker, "company": "", "row": {}})
        item["sector_notes"] = notes[:5]

    return {"source": stock_table.get("source", ""), "updated_at": now_iso(), "items": details}


def research_files() -> list[dict[str, Any]]:
    files = []
    for path in sorted(ROOT_DIR.glob("US_*.md")) + [ROOT_DIR / "README.md", ROOT_DIR / "AGENTS.md"]:
        if not path.exists():
            continue
        stat = path.stat()
        files.append(
            {
                "path": str(path.relative_to(ROOT_DIR)),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
        )
    return files


def session_path(session_id: str) -> Path:
    return CHAT_DIR / safe_token(session_id, "default")


def load_messages(session_id: str) -> list[dict[str, Any]]:
    path = session_path(session_id) / "messages.json"
    messages = read_json(path, [])
    return messages if isinstance(messages, list) else []


def save_messages(session_id: str, messages: list[dict[str, Any]]) -> None:
    write_json(session_path(session_id) / "messages.json", messages[-80:])


def compact_table_for_prompt() -> str:
    table = table_snapshot()
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    lines = ["Current LazyInvest sector matrix snapshot:"]
    for row in rows:
        parts = []
        for header in headers:
            parts.append(f"{header}: {row.get(header, '')}")
        lines.append("- " + "; ".join(parts))
    return "\n".join(lines)


def compact_stock_table_for_prompt() -> str:
    table = stock_table_snapshot()
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    lines = ["Current LazyInvest stock table snapshot:"]
    for row in rows:
        parts = []
        for header in headers:
            parts.append(f"{header}: {row.get(header, '')}")
        lines.append("- " + "; ".join(parts))
    return "\n".join(lines)


def run_codex(prompt_text: str, selected_profile: dict[str, str], output_path: Path, *, read_only: bool, timeout: int) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "codex",
        "exec",
        "--ephemeral",
        "--model",
        selected_profile["model"],
        "-c",
        f'model_reasoning_effort="{selected_profile["reasoning"]}"',
        "--cd",
        str(ROOT_DIR),
        "--output-last-message",
        str(output_path),
    ]
    if read_only:
        cmd.extend(["--sandbox", "read-only"])
    else:
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    cmd.append("-")
    started = time.time()
    try:
        proc = subprocess.run(cmd, input=prompt_text, text=True, capture_output=True, timeout=timeout, cwd=ROOT_DIR)
        final = read_text(output_path).strip()
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "message": final or proc.stdout.strip() or proc.stderr.strip(),
            "seconds": round(time.time() - started, 2),
            "command": " ".join(cmd[:-1]) + " -",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": 124,
            "stdout": str(exc.stdout or "")[-12000:],
            "stderr": str(exc.stderr or "")[-12000:] + "\nTimed out.",
            "message": "The Codex job timed out before returning a final response.",
            "seconds": round(time.time() - started, 2),
            "command": " ".join(cmd[:-1]) + " -",
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": "codex executable was not found in PATH",
            "message": "The server could not find the `codex` executable.",
            "seconds": round(time.time() - started, 2),
            "command": " ".join(cmd[:-1]) + " -",
        }


def chat_reply(session_id: str, user_message: str) -> dict[str, Any]:
    messages = load_messages(session_id)
    messages.append({"role": "user", "content": user_message, "created_at": now_iso()})
    save_messages(session_id, messages)
    history = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages[-12:])
    prompt_text = "\n\n".join(
        [
            read_text(CHAT_PROMPT_PATH),
            compact_table_for_prompt(),
            compact_stock_table_for_prompt(),
            "Recent chat history:",
            history,
            "Reply to the latest user message.",
        ]
    )
    run_dir = session_path(session_id) / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = run_codex(prompt_text, profile("chat"), run_dir / "assistant.txt", read_only=True, timeout=DEFAULT_TIMEOUT_SECONDS)
    assistant_message = result["message"] if result["ok"] else f"Chat backend error: {result['message']}"
    messages = load_messages(session_id)
    messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
            "created_at": now_iso(),
            "profile": profile("chat"),
            "ok": result["ok"],
        }
    )
    save_messages(session_id, messages)
    return {"message": assistant_message, "messages": messages, "run": result}


def job_path(job_id: str) -> Path:
    return JOB_DIR / safe_token(job_id, "job")


def load_job(job_id: str) -> dict[str, Any]:
    return read_json(job_path(job_id) / "job.json", {})


def save_job(job_id: str, job: dict[str, Any]) -> None:
    write_json(job_path(job_id) / "job.json", job)


def start_research_job(instruction: str) -> dict[str, Any]:
    job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    selected_profile = profile("research")
    job = {
        "id": job_id,
        "status": "queued",
        "instruction": instruction,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "profile": selected_profile,
    }
    save_job(job_id, job)

    def worker() -> None:
        current = load_job(job_id)
        current.update({"status": "running", "started_at": now_iso(), "updated_at": now_iso()})
        save_job(job_id, current)
        prompt_text = "\n\n".join(
            [
                read_text(RESEARCH_PROMPT_PATH),
                "Current table snapshot:",
                compact_table_for_prompt(),
                compact_stock_table_for_prompt(),
                "User request:",
                instruction,
            ]
        )
        run_dir = job_path(job_id)
        (run_dir / "prompt.txt").write_text(prompt_text, encoding="utf-8")
        result = run_codex(prompt_text, selected_profile, run_dir / "final.txt", read_only=False, timeout=RESEARCH_TIMEOUT_SECONDS)
        current = load_job(job_id)
        current.update(
            {
                "status": "completed" if result["ok"] else "failed",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
                "result": result["message"],
                "returncode": result["returncode"],
                "seconds": result["seconds"],
                "stdout_tail": result["stdout"][-6000:],
                "stderr_tail": result["stderr"][-6000:],
                "command": result["command"],
            }
        )
        save_job(job_id, current)

    thread = threading.Thread(target=worker, name=f"lazyinvest-job-{job_id}", daemon=True)
    thread.start()
    return job


def recent_jobs(limit: int = 12) -> list[dict[str, Any]]:
    jobs = []
    for path in sorted(JOB_DIR.glob("*/job.json"), reverse=True):
        job = read_json(path, {})
        if isinstance(job, dict):
            jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LazyInvest Studio</title>
  <style>
    :root {
      --bg: #f6f7f2;
      --ink: #17201c;
      --muted: #647067;
      --line: #dfe5dc;
      --panel: #ffffff;
      --panel-2: #f9faf5;
      --teal: #087f7a;
      --teal-2: #0ea5a0;
      --gold: #b87904;
      --danger: #b42318;
      --shadow: 0 18px 50px rgba(23, 32, 28, .10);
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); min-height: 100vh; }
    button, input, textarea, select { font: inherit; }
    .app { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    header {
      display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: center;
      padding: 16px 22px; border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,.88); backdrop-filter: blur(18px);
      position: sticky; top: 0; z-index: 10;
    }
    .brand { display: flex; gap: 14px; align-items: center; min-width: 0; }
    .mark {
      width: 44px; height: 44px; border-radius: 8px; display: grid; place-items: center;
      background: #0f312f; color: white; font-weight: 800; letter-spacing: 0;
      box-shadow: 0 10px 26px rgba(8,127,122,.26);
    }
    h1 { font-size: 18px; line-height: 1.2; margin: 0; letter-spacing: 0; }
    .tagline { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .header-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
    .pill {
      border: 1px solid var(--line); background: var(--panel-2); color: #23302a;
      padding: 7px 10px; border-radius: 999px; font-size: 12px; white-space: nowrap;
    }
    .shell {
      display: grid; grid-template-columns: minmax(360px, 42vw) minmax(520px, 1fr);
      gap: 16px; padding: 16px; min-height: 0;
    }
    .pane {
      background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
      box-shadow: var(--shadow); min-height: calc(100vh - 96px); overflow: hidden;
      display: grid; grid-template-rows: auto 1fr auto;
    }
    .pane-head { padding: 14px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
    .pane-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .pane-title h2 { margin: 0; font-size: 14px; letter-spacing: 0; }
    .sub { color: var(--muted); font-size: 12px; margin-top: 5px; line-height: 1.4; }
    .messages { overflow: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
    .msg { max-width: 92%; border: 1px solid var(--line); border-radius: 8px; padding: 11px 12px; line-height: 1.45; white-space: pre-wrap; font-size: 14px; }
    .msg.user { align-self: flex-end; background: #e9f7f5; border-color: #b7dedb; }
    .msg.assistant { align-self: flex-start; background: #fbfcf8; }
    .composer { border-top: 1px solid var(--line); padding: 12px; display: grid; gap: 10px; background: var(--panel-2); }
    textarea {
      resize: vertical; min-height: 92px; max-height: 220px; width: 100%;
      border: 1px solid var(--line); border-radius: 8px; padding: 11px 12px; outline: none;
      background: white; color: var(--ink); line-height: 1.45;
    }
    textarea:focus, input:focus, select:focus { border-color: var(--teal-2); box-shadow: 0 0 0 3px rgba(14,165,160,.16); }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .btn {
      border: 1px solid var(--line); background: white; color: var(--ink); border-radius: 8px;
      min-height: 38px; padding: 0 13px; display: inline-flex; align-items: center; gap: 8px;
      cursor: pointer; transition: .15s ease; font-weight: 650; font-size: 13px;
    }
    .btn:hover { border-color: #b8c7bf; transform: translateY(-1px); }
    .btn.primary { background: var(--teal); color: white; border-color: var(--teal); }
    .btn.gold { background: #fff7df; color: #664100; border-color: #ead49a; }
    .btn.ghost { background: transparent; }
    .btn:disabled { opacity: .55; cursor: not-allowed; transform: none; }
    .canvas { min-width: 0; }
    .toolbar {
      display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center;
      padding: 12px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2);
    }
    .tabs { display: inline-flex; gap: 4px; padding: 3px; border: 1px solid var(--line); border-radius: 8px; background: white; }
    .tab {
      min-height: 32px; border: 0; border-radius: 6px; background: transparent; padding: 0 10px;
      cursor: pointer; font-size: 12px; font-weight: 750; color: var(--muted);
    }
    .tab.active { background: #0f312f; color: white; }
    .search { width: 100%; border: 1px solid var(--line); border-radius: 8px; min-height: 38px; padding: 0 12px; }
    .table-wrap { overflow: auto; padding: 0; }
    table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; min-width: 1020px; }
    th, td { text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); padding: 12px 13px; line-height: 1.4; }
    th { position: sticky; top: 0; background: #f0f5ef; z-index: 1; font-size: 12px; color: #344139; }
    td:first-child, th:first-child { position: sticky; left: 0; background: inherit; z-index: 2; min-width: 190px; font-weight: 750; }
    th:first-child { z-index: 3; }
    tbody tr:nth-child(even) td { background: #fbfcf8; }
    tbody tr:hover td { background: #eef8f6; }
    code, .ticker { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    .ticker {
      color: #0c6966; font-weight: 800; border: 1px solid transparent; background: #e8f6f4;
      border-radius: 6px; padding: 1px 5px; cursor: pointer; line-height: 1.5;
    }
    .ticker:hover, .ticker:focus { border-color: #7ac4be; outline: 0; box-shadow: 0 0 0 3px rgba(14,165,160,.12); }
    td a { color: #075f5c; font-weight: 650; text-decoration-thickness: 1px; text-underline-offset: 2px; }
    .jobs { border-top: 1px solid var(--line); max-height: 220px; overflow: auto; background: #fbfcf8; }
    .job { padding: 10px 14px; border-bottom: 1px solid var(--line); display: grid; gap: 4px; font-size: 12px; }
    .job strong { font-size: 13px; }
    .ok { color: var(--teal); }
    .bad { color: var(--danger); }
    .muted { color: var(--muted); }
    dialog { border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); max-width: 560px; width: calc(100vw - 32px); }
    dialog::backdrop { background: rgba(13, 20, 17, .35); backdrop-filter: blur(4px); }
    .settings-grid { display: grid; gap: 12px; }
    .setting-row { display: grid; grid-template-columns: 120px 1fr 130px; gap: 8px; align-items: center; }
    .setting-row input, .setting-row select { min-height: 38px; border: 1px solid var(--line); border-radius: 8px; padding: 0 10px; }
    .toast {
      position: fixed; right: 16px; bottom: 16px; background: #17201c; color: white;
      padding: 10px 12px; border-radius: 8px; box-shadow: var(--shadow); display: none; max-width: 420px;
    }
    .stock-detail {
      border-top: 1px solid var(--line); padding: 14px 16px; background: #fbfcf8;
      display: grid; gap: 10px; max-height: 280px; overflow: auto;
    }
    .detail-head { display: flex; justify-content: space-between; gap: 10px; align-items: start; }
    .detail-head h3 { margin: 0; font-size: 15px; }
    .detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; font-size: 12px; }
    .detail-box { border: 1px solid var(--line); border-radius: 8px; padding: 9px 10px; background: white; min-width: 0; }
    .detail-box strong { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; }
    .analysis { white-space: pre-wrap; line-height: 1.45; font-size: 12px; color: #26332d; }
    .ticker-tip {
      position: fixed; z-index: 30; width: min(420px, calc(100vw - 24px)); display: none;
      background: #17201c; color: white; border-radius: 8px; padding: 11px 12px;
      box-shadow: 0 18px 48px rgba(0,0,0,.28); font-size: 12px; line-height: 1.4;
    }
    .ticker-tip strong { display: block; font-size: 13px; margin-bottom: 5px; }
    .ticker-tip .muted { color: #c9d4cf; }
    @media (max-width: 980px) {
      .shell { grid-template-columns: 1fr; }
      .pane { min-height: 70vh; }
      header { grid-template-columns: 1fr; }
      .header-actions { justify-content: flex-start; }
      .setting-row { grid-template-columns: 1fr; }
      .toolbar { grid-template-columns: 1fr; }
      .detail-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="brand">
        <div class="mark">LI</div>
        <div>
          <h1>LazyInvest Studio</h1>
          <p class="tagline">Chat, deep research jobs, stock hover details, and live Markdown tables for LazyInvest.</p>
        </div>
      </div>
      <div class="header-actions">
        <span class="pill" id="chatProfile">chat: gpt-5.5 / medium</span>
        <span class="pill" id="researchProfile">research: gpt-5.5 / xhigh</span>
        <a class="btn ghost" href="https://earn.lazying.art" target="_blank" rel="noreferrer">earn.lazying.art</a>
        <button class="btn" id="settingsBtn">Settings</button>
      </div>
    </header>
    <main class="shell">
      <section class="pane">
        <div class="pane-head">
          <div class="pane-title">
            <h2>Research Chat</h2>
            <button class="btn ghost" id="newSessionBtn">New Session</button>
          </div>
          <div class="sub">Fast chat uses <strong>gpt-5.5 / medium</strong> in read-only mode. Use the Research Agent for table-changing work.</div>
        </div>
        <div class="messages" id="messages"></div>
        <div class="composer">
          <textarea id="messageInput" placeholder="Ask about sectors, tickers, risks, or tell the backend agent what to update."></textarea>
          <div class="row">
            <button class="btn primary" id="sendBtn">Send Chat</button>
            <button class="btn gold" id="researchBtn">Research & Maintain Table</button>
            <button class="btn" id="reloadBtn">Reload Table</button>
          </div>
        </div>
      </section>
      <section class="pane canvas">
        <div class="pane-head">
          <div class="pane-title">
            <h2>Research Canvas</h2>
            <span class="pill" id="tableMeta">loading</span>
          </div>
          <div class="sub">Right canvas is parsed from maintained Markdown tables. Hover or click a ticker for stock detail.</div>
        </div>
        <div class="toolbar">
          <div class="tabs" aria-label="Canvas view">
            <button class="tab active" data-canvas="sector" id="sectorTab">Sectors</button>
            <button class="tab" data-canvas="stocks" id="stocksTab">Stocks</button>
          </div>
          <input class="search" id="filterInput" placeholder="Filter sectors, tickers, or risk notes" />
          <div class="row">
            <a class="btn" href="/file/US_Sector_Investment_Matrix_2026-06-13.md" target="_blank" id="openCurrentFile">Open Matrix</a>
          </div>
        </div>
        <div class="table-wrap">
          <table id="sectorTable"></table>
        </div>
        <div class="stock-detail" id="stockDetail"></div>
        <div class="jobs" id="jobs"></div>
      </section>
    </main>
  </div>
  <dialog id="settingsDialog">
    <form method="dialog">
      <div class="pane-title">
        <h2>Model Settings</h2>
        <button class="btn" value="close">Close</button>
      </div>
      <p class="sub">Defaults match the requested split: chat is medium, backend research and agent work are xhigh.</p>
      <div class="settings-grid" id="settingsGrid"></div>
      <div class="row" style="margin-top:14px; justify-content:flex-end;">
        <button class="btn primary" id="saveSettingsBtn" value="default">Save Settings</button>
      </div>
    </form>
  </dialog>
  <div class="toast" id="toast"></div>
  <div class="ticker-tip" id="tickerTip"></div>
  <script>
    const state = {
      sessionId: localStorage.lazyinvestSession || makeSession(),
      table: null,
      stockTable: null,
      stockDetails: {},
      settings: null,
      polling: new Set(),
      canvas: localStorage.lazyinvestCanvas || "sector",
      selectedTicker: null
    };
    localStorage.lazyinvestSession = state.sessionId;

    function makeSession() {
      return new Date().toISOString().replace(/[-:.]/g, "").slice(0, 15) + "-" + Math.random().toString(16).slice(2, 8);
    }
    async function api(path, payload) {
      const options = payload === undefined ? {} : { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) };
      const res = await fetch(path, options);
      const data = await res.json();
      if (!res.ok || data.ok === false) throw new Error(data.error || data.message || res.statusText);
      return data;
    }
    function toast(text) {
      const el = document.getElementById("toast");
      el.textContent = text; el.style.display = "block";
      setTimeout(() => { el.style.display = "none"; }, 3600);
    }
    function renderMessages(messages) {
      const box = document.getElementById("messages");
      box.innerHTML = "";
      if (!messages || !messages.length) {
        box.innerHTML = '<div class="msg assistant">Ask a question, or use <strong>Research & Maintain Table</strong> to launch a backend xhigh agent job.</div>';
        return;
      }
      for (const msg of messages) {
        const div = document.createElement("div");
        div.className = "msg " + (msg.role === "user" ? "user" : "assistant");
        div.textContent = msg.content || "";
        box.appendChild(div);
      }
      box.scrollTop = box.scrollHeight;
    }
    function renderProfiles() {
      const p = state.settings?.profiles || {};
      document.getElementById("chatProfile").textContent = `chat: ${p.chat?.model || "gpt-5.5"} / ${p.chat?.reasoning || "medium"}`;
      document.getElementById("researchProfile").textContent = `research: ${p.research?.model || "gpt-5.5"} / ${p.research?.reasoning || "xhigh"}`;
    }
    function currentTable() {
      return state.canvas === "stocks" ? state.stockTable : state.table;
    }
    function renderCanvasTabs() {
      document.querySelectorAll("[data-canvas]").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.canvas === state.canvas);
      });
      const link = document.getElementById("openCurrentFile");
      const table = currentTable();
      if (table?.source) {
        link.href = "/file/" + table.source;
        link.textContent = state.canvas === "stocks" ? "Open Stocks" : "Open Matrix";
      }
    }
    function renderTable() {
      const table = currentTable();
      const el = document.getElementById("sectorTable");
      const meta = document.getElementById("tableMeta");
      if (!table || !table.headers?.length) {
        el.innerHTML = "<tbody><tr><td>No table found.</td></tr></tbody>";
        meta.textContent = "no table";
        return;
      }
      const unit = state.canvas === "stocks" ? "stocks" : "sectors";
      meta.textContent = `${table.source} · ${table.rows.length} ${unit}`;
      const needle = document.getElementById("filterInput").value.trim().toLowerCase();
      const rows = table.rows.filter(row => JSON.stringify(row).toLowerCase().includes(needle));
      const thead = `<thead><tr>${table.headers.map(h => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>`;
      const tbody = rows.map(row => `<tr>${table.headers.map(h => `<td>${formatCell(row[h] || "", h)}</td>`).join("")}</tr>`).join("");
      el.innerHTML = thead + `<tbody>${tbody}</tbody>`;
      renderCanvasTabs();
      renderStockDetail(state.selectedTicker);
    }
    function tickerButton(symbol) {
      const safe = escapeHtml(symbol);
      return `<button type="button" class="ticker" data-ticker="${safe}">${safe}</button>`;
    }
    function formatCell(value, header = "") {
      let text = escapeHtml(value);
      text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
      text = text.replace(/`([A-Z][A-Z0-9.]{0,9})`/g, (_, ticker) => tickerButton(ticker));
      const plain = String(value || "").replace(/`/g, "").trim();
      if (header.toLowerCase().includes("ticker") && /^[A-Z][A-Z0-9.]{0,9}$/.test(plain)) {
        return tickerButton(plain);
      }
      return text;
    }
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));
    }
    function detailForTicker(symbol) {
      return state.stockDetails?.[symbol] || null;
    }
    function cleanText(value, limit = 900) {
      const text = String(value || "").replace(/\s+/g, " ").trim();
      return text.length > limit ? text.slice(0, limit - 1) + "..." : text;
    }
    function renderStockDetail(symbol) {
      const el = document.getElementById("stockDetail");
      if (!symbol) {
        el.innerHTML = '<div class="muted">Stock detail appears here after selecting a ticker.</div>';
        return;
      }
      const detail = detailForTicker(symbol);
      if (!detail) {
        el.innerHTML = `<div class="detail-head"><h3>${tickerButton(symbol)}</h3><span class="pill">No maintained row yet</span></div>`;
        return;
      }
      const title = `${escapeHtml(symbol)}${detail.company ? " · " + escapeHtml(detail.company) : ""}`;
      const boxes = [
        ["Bucket", detail.bucket],
        ["Category", detail.category],
        ["Why It Matters", detail.why],
        ["Evidence", detail.evidence],
        ["Risks", detail.risks],
        ["Monitor", detail.monitor]
      ].filter(([, value]) => value);
      const sectorNotes = (detail.sector_notes || []).map(note => "- " + note).join("\n");
      const analysis = detail.analysis || sectorNotes || "No deep analysis section has been linked yet.";
      el.innerHTML = `
        <div class="detail-head">
          <h3>${tickerButton(symbol)} ${title.replace(escapeHtml(symbol), "")}</h3>
          <span class="pill">${escapeHtml(detail.source ? "source linked" : "repo note")}</span>
        </div>
        <div class="detail-grid">
          ${boxes.map(([label, value]) => `<div class="detail-box"><strong>${escapeHtml(label)}</strong>${formatCell(value)}</div>`).join("")}
        </div>
        <div class="detail-box">
          <strong>Deep Analysis</strong>
          <div class="analysis">${escapeHtml(cleanText(analysis, 2600))}</div>
        </div>
        ${detail.source ? `<div class="detail-box"><strong>Primary Source</strong>${formatCell(detail.source)}</div>` : ""}
      `;
    }
    function showTickerTip(symbol, target) {
      const tip = document.getElementById("tickerTip");
      const detail = detailForTicker(symbol);
      const title = detail?.company ? `${symbol} · ${detail.company}` : symbol;
      const body = detail
        ? [detail.bucket, detail.why, detail.evidence, detail.risks ? "Risk: " + detail.risks : ""].filter(Boolean).join(" ")
        : "No maintained stock row yet. Click to inspect any sector note available in the repo.";
      tip.innerHTML = `<strong>${escapeHtml(title)}</strong><div>${escapeHtml(cleanText(body, 520))}</div><div class="muted">Click ticker to pin deep analysis.</div>`;
      tip.style.display = "block";
      const rect = target.getBoundingClientRect();
      const top = Math.min(window.innerHeight - tip.offsetHeight - 12, rect.bottom + 8);
      const left = Math.min(window.innerWidth - tip.offsetWidth - 12, Math.max(12, rect.left));
      tip.style.top = `${Math.max(12, top)}px`;
      tip.style.left = `${left}px`;
    }
    function hideTickerTip() {
      document.getElementById("tickerTip").style.display = "none";
    }
    function selectTicker(symbol) {
      state.selectedTicker = symbol;
      renderStockDetail(symbol);
    }
    function renderJobs(jobs) {
      const box = document.getElementById("jobs");
      if (!jobs || !jobs.length) {
        box.innerHTML = '<div class="job muted">No research jobs yet.</div>';
        return;
      }
      box.innerHTML = jobs.map(job => {
        const statusClass = job.status === "completed" ? "ok" : (job.status === "failed" ? "bad" : "");
        const result = job.result ? `<div>${escapeHtml(job.result).slice(0, 500)}</div>` : "";
        return `<div class="job"><strong>${escapeHtml(job.instruction || job.id)}</strong><span class="${statusClass}">${escapeHtml(job.status || "")} · ${escapeHtml(job.profile?.model || "")} / ${escapeHtml(job.profile?.reasoning || "")}</span>${result}</div>`;
      }).join("");
      for (const job of jobs) {
        if ((job.status === "queued" || job.status === "running") && !state.polling.has(job.id)) {
          pollJob(job.id);
        }
      }
    }
    async function loadState() {
      const data = await api(`/api/state?session_id=${encodeURIComponent(state.sessionId)}`);
      state.settings = data.settings;
      state.table = data.table;
      state.stockTable = data.stock_table;
      state.stockDetails = data.stock_details?.items || {};
      renderProfiles();
      renderMessages(data.messages);
      renderTable();
      renderJobs(data.jobs);
    }
    async function sendChat() {
      const input = document.getElementById("messageInput");
      const message = input.value.trim();
      if (!message) return;
      input.value = "";
      document.getElementById("sendBtn").disabled = true;
      toast("Chat profile running: gpt-5.5 / medium");
      try {
        const data = await api("/api/chat", { session_id: state.sessionId, message });
        renderMessages(data.messages);
      } catch (err) {
        toast(err.message);
        await loadState();
      } finally {
        document.getElementById("sendBtn").disabled = false;
      }
    }
    async function startResearch() {
      const input = document.getElementById("messageInput");
      const instruction = input.value.trim() || "Refresh the sector investment matrix and maintained stock table with current evidence.";
      document.getElementById("researchBtn").disabled = true;
      try {
        const data = await api("/api/research/jobs", { instruction });
        toast("Research agent started: " + data.job.id);
        await loadState();
      } catch (err) {
        toast(err.message);
      } finally {
        document.getElementById("researchBtn").disabled = false;
      }
    }
    async function pollJob(id) {
      state.polling.add(id);
      let active = true;
      while (active) {
        await new Promise(resolve => setTimeout(resolve, 3000));
        try {
          const data = await api(`/api/research/job?id=${encodeURIComponent(id)}`);
          if (data.job.status === "completed" || data.job.status === "failed") {
            active = false;
            state.polling.delete(id);
            await loadState();
            toast(data.job.status === "completed" ? "Research job completed." : "Research job failed.");
          } else {
            const jobs = await api("/api/research/jobs");
            renderJobs(jobs.jobs);
          }
        } catch (err) {
          active = false;
          state.polling.delete(id);
        }
      }
    }
    function renderSettingsForm() {
      const profiles = state.settings?.profiles || {};
      const grid = document.getElementById("settingsGrid");
      grid.innerHTML = ["chat", "research", "agent"].map(name => {
        const p = profiles[name] || {};
        return `<label class="setting-row"><strong>${name}</strong><input data-profile="${name}" data-key="model" value="${escapeHtml(p.model || "gpt-5.5")}"><select data-profile="${name}" data-key="reasoning">${["low","medium","high","xhigh"].map(level => `<option ${level === (p.reasoning || "medium") ? "selected" : ""}>${level}</option>`).join("")}</select></label>`;
      }).join("");
    }
    async function saveSettings(event) {
      event.preventDefault();
      const profiles = {};
      document.querySelectorAll("[data-profile]").forEach(el => {
        profiles[el.dataset.profile] ||= {};
        profiles[el.dataset.profile][el.dataset.key] = el.value;
      });
      try {
        const data = await api("/api/settings", { profiles });
        state.settings = data.settings;
        renderProfiles();
        document.getElementById("settingsDialog").close();
        toast("Settings saved.");
      } catch (err) {
        toast(err.message);
      }
    }
    document.getElementById("sendBtn").addEventListener("click", sendChat);
    document.getElementById("researchBtn").addEventListener("click", startResearch);
    document.getElementById("reloadBtn").addEventListener("click", loadState);
    document.getElementById("filterInput").addEventListener("input", renderTable);
    document.querySelectorAll("[data-canvas]").forEach(btn => {
      btn.addEventListener("click", () => {
        state.canvas = btn.dataset.canvas;
        localStorage.lazyinvestCanvas = state.canvas;
        renderTable();
      });
    });
    document.getElementById("sectorTable").addEventListener("mouseover", event => {
      const ticker = event.target.closest?.("[data-ticker]");
      if (ticker) showTickerTip(ticker.dataset.ticker, ticker);
    });
    document.getElementById("sectorTable").addEventListener("mouseout", event => {
      if (event.target.closest?.("[data-ticker]")) hideTickerTip();
    });
    document.getElementById("sectorTable").addEventListener("focusin", event => {
      const ticker = event.target.closest?.("[data-ticker]");
      if (ticker) showTickerTip(ticker.dataset.ticker, ticker);
    });
    document.getElementById("sectorTable").addEventListener("focusout", hideTickerTip);
    document.getElementById("sectorTable").addEventListener("click", event => {
      const ticker = event.target.closest?.("[data-ticker]");
      if (ticker) selectTicker(ticker.dataset.ticker);
    });
    document.getElementById("newSessionBtn").addEventListener("click", () => {
      state.sessionId = makeSession();
      localStorage.lazyinvestSession = state.sessionId;
      renderMessages([]);
    });
    document.getElementById("settingsBtn").addEventListener("click", () => {
      renderSettingsForm();
      document.getElementById("settingsDialog").showModal();
    });
    document.getElementById("saveSettingsBtn").addEventListener("click", saveSettings);
    document.getElementById("messageInput").addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") sendChat();
    });
    loadState().catch(err => toast(err.message));
  </script>
</body>
</html>
"""


class LazyInvestHandler(BaseHTTPRequestHandler):
    server_version = "LazyInvestStudio/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        syslog = f"{self.address_string()} - {fmt % args}\n"
        print(syslog, end="")

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, content_type: str = "text/plain; charset=utf-8", status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self.send_text(INDEX_HTML, "text/html; charset=utf-8")
                return
            if parsed.path == "/api/state":
                session_id = parse_qs(parsed.query).get("session_id", ["default"])[0]
                self.send_json(
                    {
                        "ok": True,
                        "settings": load_settings(),
                        "table": table_snapshot(),
                        "stock_table": stock_table_snapshot(),
                        "stock_details": stock_details_snapshot(),
                        "files": research_files(),
                        "messages": load_messages(session_id),
                        "jobs": recent_jobs(),
                    }
                )
                return
            if parsed.path == "/api/table":
                self.send_json({"ok": True, "table": table_snapshot()})
                return
            if parsed.path == "/api/stocks":
                self.send_json({"ok": True, "table": stock_table_snapshot(), "details": stock_details_snapshot()})
                return
            if parsed.path == "/api/settings":
                self.send_json({"ok": True, "settings": load_settings()})
                return
            if parsed.path == "/api/research/jobs":
                self.send_json({"ok": True, "jobs": recent_jobs()})
                return
            if parsed.path == "/api/research/job":
                job_id = parse_qs(parsed.query).get("id", [""])[0]
                job = load_job(job_id)
                self.send_json({"ok": bool(job), "job": job}, status=200 if job else 404)
                return
            if parsed.path.startswith("/file/"):
                rel = parsed.path.removeprefix("/file/")
                candidate = (ROOT_DIR / rel).resolve()
                if ROOT_DIR.resolve() not in candidate.parents or not candidate.is_file():
                    self.send_json({"ok": False, "error": "file not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_text(read_text(candidate), "text/markdown; charset=utf-8")
                return
            self.send_json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            payload = self.read_body()
            if parsed.path == "/api/chat":
                session_id = str(payload.get("session_id") or "default")
                message = str(payload.get("message") or "").strip()
                if not message:
                    raise ValueError("message is required")
                result = chat_reply(session_id, message)
                self.send_json({"ok": True, **result})
                return
            if parsed.path == "/api/research/jobs":
                instruction = str(payload.get("instruction") or "").strip()
                if not instruction:
                    raise ValueError("instruction is required")
                job = start_research_job(instruction)
                self.send_json({"ok": True, "job": job})
                return
            if parsed.path == "/api/settings":
                settings = sanitize_settings(payload)
                write_json(SETTINGS_PATH, settings)
                self.send_json({"ok": True, "settings": settings})
                return
            self.send_json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LazyInvest Studio.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    ensure_dirs()
    if not SETTINGS_PATH.exists():
        write_json(SETTINGS_PATH, DEFAULT_SETTINGS)
    server = ThreadingHTTPServer((args.host, args.port), LazyInvestHandler)
    print(f"LazyInvest Studio listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping LazyInvest Studio")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
