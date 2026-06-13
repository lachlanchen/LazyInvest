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


def matrix_path() -> Path:
    settings = load_settings()
    source = str((settings.get("table") or {}).get("source") or DEFAULT_MATRIX.name)
    candidate = (ROOT_DIR / source).resolve()
    if ROOT_DIR.resolve() not in candidate.parents and candidate != ROOT_DIR.resolve():
        return DEFAULT_MATRIX
    return candidate


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
        "source": matrix_path().name,
        "updated_at": now_iso(),
    }


def table_snapshot() -> dict[str, Any]:
    path = matrix_path()
    text = read_text(path)
    settings = load_settings()
    heading = str((settings.get("table") or {}).get("heading") or "Maintained Sector Table")
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
      display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center;
      padding: 12px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2);
    }
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
    .ticker { color: #0c6966; font-weight: 800; }
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
    @media (max-width: 980px) {
      .shell { grid-template-columns: 1fr; }
      .pane { min-height: 70vh; }
      header { grid-template-columns: 1fr; }
      .header-actions { justify-content: flex-start; }
      .setting-row { grid-template-columns: 1fr; }
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
          <p class="tagline">Chat, deep research jobs, and a live sector-table canvas for LazyInvest.</p>
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
            <h2>Sector Table Canvas</h2>
            <span class="pill" id="tableMeta">loading</span>
          </div>
          <div class="sub">Right canvas is parsed from the maintained Markdown matrix. Completed research jobs refresh this view.</div>
        </div>
        <div class="toolbar">
          <input class="search" id="filterInput" placeholder="Filter sectors, tickers, or risk notes" />
          <div class="row">
            <a class="btn" href="/file/US_Sector_Investment_Matrix_2026-06-13.md" target="_blank">Open Matrix</a>
          </div>
        </div>
        <div class="table-wrap">
          <table id="sectorTable"></table>
        </div>
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
  <script>
    const state = { sessionId: localStorage.lazyinvestSession || makeSession(), table: null, settings: null, polling: new Set() };
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
    function renderTable() {
      const table = state.table;
      const el = document.getElementById("sectorTable");
      const meta = document.getElementById("tableMeta");
      if (!table || !table.headers?.length) {
        el.innerHTML = "<tbody><tr><td>No table found.</td></tr></tbody>";
        meta.textContent = "no table";
        return;
      }
      meta.textContent = `${table.source} · ${table.rows.length} sectors`;
      const needle = document.getElementById("filterInput").value.trim().toLowerCase();
      const rows = table.rows.filter(row => JSON.stringify(row).toLowerCase().includes(needle));
      const thead = `<thead><tr>${table.headers.map(h => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>`;
      const tbody = rows.map(row => `<tr>${table.headers.map(h => `<td>${formatCell(row[h] || "")}</td>`).join("")}</tr>`).join("");
      el.innerHTML = thead + `<tbody>${tbody}</tbody>`;
    }
    function formatCell(value) {
      return escapeHtml(value).replace(/`([^`]+)`/g, '<span class="ticker">$1</span>');
    }
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));
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
      const instruction = input.value.trim() || "Refresh the sector investment matrix with current evidence and maintain the table.";
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
                        "files": research_files(),
                        "messages": load_messages(session_id),
                        "jobs": recent_jobs(),
                    }
                )
                return
            if parsed.path == "/api/table":
                self.send_json({"ok": True, "table": table_snapshot()})
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
