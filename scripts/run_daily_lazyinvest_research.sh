#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/run_daily_lazyinvest_research.sh [options]

Runs one automated LazyInvest deep-research refresh for the current local day.
The runner calls Codex, validates research Markdown, commits changes, and pushes.

Options:
  --force             run even if today's success marker already exists
  --dry-run           validate setup and print the planned action; do not run Codex
  --no-push           commit locally but skip git push
  --model <model>     Codex model (default: gpt-5.5)
  --reasoning <level> reasoning effort: low, medium, high, xhigh (default: xhigh)
  --remote <name>     git remote to push (default: origin)
  --branch <name>     git branch to refresh and push (default: current branch or main)
  --cron-time HH:MM   time used by --install-cron (default: 07:30)
  --install-cron      install or replace a daily crontab entry for this script
  --print-cron        print the crontab line without installing it
  -h, --help          show this help

Environment:
  LAZYINVEST_TZ                    local date timezone (default: Asia/Hong_Kong)
  LAZYINVEST_RESEARCH_MODEL        default model override
  LAZYINVEST_RESEARCH_REASONING    default reasoning override
  LAZYINVEST_CODEX_TIMEOUT_SECONDS max Codex runtime (default: 7200)
  LAZYINVEST_EXTRA_INSTRUCTION     appended to the research prompt
  LAZYINVEST_UPDATE_SCREENSHOT     set to 0 to skip screenshot refresh
  LAZYINVEST_SCREENSHOT_PORT       local Studio port for screenshot (default: 8792)
  LAZYINVEST_SCREENSHOT_CANVAS     screenshot canvas tab (default: history)
  LAZYINVEST_REPORTS_ENABLED       set to 0 to skip separate PDF report archive
  LAZYINVEST_REPORTS_DIR           report repo path (default: ../LazyInvestReports)
  LAZYINVEST_CRON_COMMAND          command used by --install-cron
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
TZ_NAME="${LAZYINVEST_TZ:-Asia/Hong_Kong}"
TODAY="$(TZ="$TZ_NAME" date +%F)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
DATA_DIR="$ROOT_DIR/data/daily-research"
LOG_DIR="$DATA_DIR/logs"
RUN_DIR="$DATA_DIR/runs/${TODAY}_${RUN_ID}"
LOCK_DIR="$DATA_DIR/.lock"
LAST_SUCCESS_FILE="$DATA_DIR/last_success_date"
PROMPT_FILE="$RUN_DIR/prompt.md"
AGENT_OUTPUT="$RUN_DIR/final.md"
MODEL="${LAZYINVEST_RESEARCH_MODEL:-gpt-5.5}"
REASONING="${LAZYINVEST_RESEARCH_REASONING:-xhigh}"
REMOTE="${LAZYINVEST_REMOTE:-origin}"
BRANCH="${LAZYINVEST_BRANCH:-}"
CODEX_TIMEOUT_SECONDS="${LAZYINVEST_CODEX_TIMEOUT_SECONDS:-7200}"
CRON_TIME="${LAZYINVEST_CRON_TIME:-07:30}"
UPDATE_SCREENSHOT="${LAZYINVEST_UPDATE_SCREENSHOT:-1}"
SCREENSHOT_PORT="${LAZYINVEST_SCREENSHOT_PORT:-8792}"
SCREENSHOT_CANVAS="${LAZYINVEST_SCREENSHOT_CANVAS:-history}"
SCREENSHOT_PATH="$ROOT_DIR/figs/lazyinvest-studio.png"
REPORTS_ENABLED="${LAZYINVEST_REPORTS_ENABLED:-1}"
REPORTS_DIR="${LAZYINVEST_REPORTS_DIR:-$ROOT_DIR/../LazyInvestReports}"
FORCE=0
DRY_RUN=0
NO_PUSH=0
INSTALL_CRON=0
PRINT_CRON=0
MARKER="# LazyInvest daily research"

log() {
  printf '[%s] %s\n' "$(TZ="$TZ_NAME" date '+%Y-%m-%d %H:%M:%S %Z')" "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

quote_for_sh() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

cron_path_value() {
  if [[ -n "${LAZYINVEST_CRON_PATH:-}" ]]; then
    printf '%s' "$LAZYINVEST_CRON_PATH"
    return
  fi

  local value="/usr/local/bin:/usr/bin:/bin"
  local bin dir
  for bin in codex git bash rg python3 curl google-chrome chromium chromium-browser; do
    if command -v "$bin" >/dev/null 2>&1; then
      dir="$(dirname "$(command -v "$bin")")"
      case ":$value:" in
        *":$dir:"*) ;;
        *) value="$dir:$value" ;;
      esac
    fi
  done
  printf '%s' "$value"
}

cron_command_path() {
  if [[ -n "${LAZYINVEST_CRON_COMMAND:-}" ]]; then
    printf '%s' "$LAZYINVEST_CRON_COMMAND"
    return
  fi

  local tmux_wrapper="${HOME:-/home/lachlan}/scripts/lazyinvest_daily_analysis_tmux.sh"
  if [[ -x "$tmux_wrapper" ]]; then
    printf '%s' "$tmux_wrapper"
  else
    printf '%s' "$SCRIPT_PATH"
  fi
}

validate_research_text() {
  local pattern="not personal financial advice|Source:|Sources:|Date:"
  if command -v rg >/dev/null 2>&1; then
    rg -n "$pattern" README.md US_*.md >/dev/null
  else
    grep -REn "$pattern" README.md US_*.md >/dev/null
  fi
}

find_chrome() {
  local candidate
  for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

capture_studio_screenshot() {
  [[ "$UPDATE_SCREENSHOT" == "0" ]] && {
    log "Skipping screenshot refresh because LAZYINVEST_UPDATE_SCREENSHOT=0."
    return 0
  }

  local chrome url base_url server_pid=""
  chrome="$(find_chrome)" || die "No Chrome/Chromium executable found for screenshot refresh"
  base_url="http://127.0.0.1:${SCREENSHOT_PORT}"
  url="${base_url}/?canvas=${SCREENSHOT_CANVAS}&date=${TODAY}"
  mkdir -p "$(dirname "$SCREENSHOT_PATH")"

  if ! curl -fsS "${base_url}/api/state?session_id=screenshot-check" >/dev/null 2>&1; then
    log "Starting temporary LazyInvest Studio server for screenshot on ${base_url}"
    python3 scripts/lazyinvest_studio.py --host 127.0.0.1 --port "$SCREENSHOT_PORT" >/tmp/lazyinvest-screenshot-server.log 2>&1 &
    server_pid="$!"
    for _ in $(seq 1 30); do
      if curl -fsS "${base_url}/api/state?session_id=screenshot-check" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    curl -fsS "${base_url}/api/state?session_id=screenshot-check" >/dev/null 2>&1 || die "temporary Studio server did not become ready"
  fi

  log "Refreshing Studio screenshot: $SCREENSHOT_PATH"
  if command -v timeout >/dev/null 2>&1; then
    timeout 120s "$chrome" --headless --disable-gpu --no-sandbox --window-size=1440,1000 --virtual-time-budget=3000 --screenshot="$SCREENSHOT_PATH" "$url" >/tmp/lazyinvest-screenshot-chrome.log 2>&1
  else
    "$chrome" --headless --disable-gpu --no-sandbox --window-size=1440,1000 --virtual-time-budget=3000 --screenshot="$SCREENSHOT_PATH" "$url" >/tmp/lazyinvest-screenshot-chrome.log 2>&1
  fi
  [[ -s "$SCREENSHOT_PATH" ]] || die "screenshot was not created"

  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" >/dev/null 2>&1 || true
  fi
}

cron_line() {
  local hour minute
  [[ "$CRON_TIME" =~ ^([0-9]{1,2}):([0-9]{2})$ ]] || die "Invalid --cron-time: $CRON_TIME"
  hour="${BASH_REMATCH[1]}"
  minute="${BASH_REMATCH[2]}"
  ((10#$hour >= 0 && 10#$hour <= 23)) || die "Invalid cron hour: $hour"
  ((10#$minute >= 0 && 10#$minute <= 59)) || die "Invalid cron minute: $minute"
  printf '%s %s * * * cd %s && PATH=%s %s >/dev/null 2>&1 %s\n' \
    "$minute" \
    "$hour" \
    "$(quote_for_sh "$ROOT_DIR")" \
    "$(quote_for_sh "$(cron_path_value)")" \
    "$(quote_for_sh "$(cron_command_path)")" \
    "$MARKER"
}

install_cron() {
  command -v crontab >/dev/null 2>&1 || die "crontab not found"
  local line
  line="$(cron_line)"
  {
    crontab -l 2>/dev/null | grep -vF "$MARKER" || true
    printf '%s\n' "$line"
  } | crontab -
  log "Installed daily crontab entry:"
  log "$line"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-push) NO_PUSH=1; shift ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --reasoning) REASONING="${2:-}"; shift 2 ;;
    --remote) REMOTE="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --cron-time) CRON_TIME="${2:-}"; shift 2 ;;
    --install-cron) INSTALL_CRON=1; shift ;;
    --print-cron) PRINT_CRON=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

[[ "$MODEL" =~ ^[A-Za-z0-9._:-]+$ ]] || die "Invalid model: $MODEL"
case "$REASONING" in
  low|medium|high|xhigh) ;;
  *) die "Invalid reasoning: $REASONING" ;;
esac
[[ "$CODEX_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || die "Invalid timeout: $CODEX_TIMEOUT_SECONDS"

mkdir -p "$LOG_DIR" "$RUN_DIR"
LOG_FILE="$LOG_DIR/daily_${TODAY}_${RUN_ID}.log"
exec > >(tee -a "$LOG_FILE") 2>&1

cd "$ROOT_DIR"

if [[ "$PRINT_CRON" -eq 1 ]]; then
  cron_line
  exit 0
fi

if [[ "$INSTALL_CRON" -eq 1 ]]; then
  install_cron
  exit 0
fi

command -v git >/dev/null 2>&1 || die "git not found"
command -v codex >/dev/null 2>&1 || die "codex not found"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  log "Another daily research run appears to be active: $LOCK_DIR"
  exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ -z "$BRANCH" ]]; then
  BRANCH="$CURRENT_BRANCH"
fi
if [[ "$BRANCH" == "HEAD" ]]; then
  BRANCH="main"
fi
[[ "$CURRENT_BRANCH" == "$BRANCH" ]] || die "current branch is $CURRENT_BRANCH, expected $BRANCH"

if [[ "$FORCE" -eq 0 && -f "$LAST_SUCCESS_FILE" && "$(tr -d '[:space:]' < "$LAST_SUCCESS_FILE")" == "$TODAY" ]]; then
  log "Daily research already completed for $TODAY in $TZ_NAME. Use --force to run again."
  exit 0
fi

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  git status --short --untracked-files=all
  die "worktree is dirty before research; refusing to mix automated changes with manual edits"
fi

log "LazyInvest daily research date: $TODAY ($TZ_NAME)"
log "Model profile: $MODEL / $REASONING"
log "Branch target: $REMOTE/$BRANCH"
log "Log file: $LOG_FILE"

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Dry run only. Would fetch, run Codex, validate, commit, and push if files changed."
  exit 0
fi

git fetch "$REMOTE" "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"

cat > "$PROMPT_FILE" <<PROMPT
# LazyInvest Daily Deep Research Refresh

Today is $TODAY in $TZ_NAME.

Use the profile below and complete one daily research maintenance pass.

$(sed -n '1,240p' "$ROOT_DIR/prompts/lazyinvest-research-agent.md")

## Daily Job

- Treat this as an independent daily research run, not an incremental copy edit. Re-check the current market regime, rates/liquidity context, sector evidence, filings, company IR pages, guidance, catalysts, and risks before changing conclusions.
- Deeply research current U.S. public-company and sector evidence using current primary sources whenever possible: SEC filings, company investor relations, earnings releases, transcripts when available, exchange/market data, FRED/Treasury/Federal Reserve data, and reputable market data.
- Use command-line and internet tools to inspect current sources. Do not fabricate or infer stale market data. If a data point cannot be refreshed, state the limitation and keep the claim dated.
- Refresh the maintained table in \`US_Sector_Investment_Matrix_2026-06-13.md\` under \`## Maintained Sector Table\`.
- Refresh the maintained stock table in \`US_Stock_Research_Table_2026-06-13.md\` under \`## Maintained Stock Table\`.
- Refresh the single best huge-growth choice note in \`US_Best_Growth_Choice_2026-06-13.md\`.
- Keep the same table columns so LazyInvest Studio can keep parsing the right canvas.
- Keep the stock table, single best choice annotation, and deeper stock analysis sections in \`US_Underfollowed_Growth_Stocks_2026-06-13.md\` aligned.
- Update file dates, market-data context, source links, nearby sector notes, and stock detail notes when tables change.
- If the underfollowed-growth note needs a directly related update, keep it scoped and evidence-linked.
- Keep this as a research watchlist, not personal financial advice.
- Do not commit or push. This shell runner validates, commits, and pushes after you finish.
- Before your final response, run \`git diff --check\` and inspect the changed Markdown.

Extra operator instruction:
${LAZYINVEST_EXTRA_INSTRUCTION:-No extra instruction.}
PROMPT

log "Prompt written to $PROMPT_FILE"

codex_cmd=(
  codex exec
  --ephemeral
  --model "$MODEL"
  -c "model_reasoning_effort=\"$REASONING\""
  --cd "$ROOT_DIR"
  --output-last-message "$AGENT_OUTPUT"
  --dangerously-bypass-approvals-and-sandbox
  -
)

log "Starting Codex daily research job"
if command -v timeout >/dev/null 2>&1; then
  timeout "${CODEX_TIMEOUT_SECONDS}s" "${codex_cmd[@]}" < "$PROMPT_FILE"
else
  "${codex_cmd[@]}" < "$PROMPT_FILE"
fi
log "Codex job finished. Final response: $AGENT_OUTPUT"

log "Updating best-choice history"
python3 scripts/update_best_choice_history.py --date "$TODAY"
capture_studio_screenshot

if [[ "$REPORTS_ENABLED" == "0" ]]; then
  log "Skipping separate report archive because LAZYINVEST_REPORTS_ENABLED=0."
else
  log "Generating independent LazyInvestReports daily archive"
  report_args=(
    --date "$TODAY"
    --reports-dir "$REPORTS_DIR"
    --model "$MODEL"
    --reasoning "$REASONING"
  )
  if [[ "$NO_PUSH" -eq 1 ]]; then
    report_args+=(--no-push)
  fi
  scripts/run_daily_lazyinvest_report.sh "${report_args[@]}"
fi

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  log "Changed files after research:"
  git status --short --untracked-files=all
else
  log "No files changed. Marking $TODAY as completed."
  printf '%s\n' "$TODAY" > "$LAST_SUCCESS_FILE"
  exit 0
fi

log "Running validation"
git diff --check
validate_research_text

shopt -s nullglob
stage_paths=(US_*.md README.md data/settings.json i18n/README.*.md figs/lazyinvest-studio.png)
if [[ "${#stage_paths[@]}" -eq 0 ]]; then
  die "no eligible research files found to stage"
fi
git add -- "${stage_paths[@]}"

if ! git diff --quiet; then
  git diff --name-only
  die "unexpected unstaged tracked changes remain after staging eligible research files"
fi

untracked="$(git ls-files --others --exclude-standard)"
if [[ -n "$untracked" ]]; then
  printf '%s\n' "$untracked"
  die "unexpected untracked files remain after research"
fi

if git diff --cached --quiet; then
  log "No eligible staged research changes. Marking $TODAY as completed."
  printf '%s\n' "$TODAY" > "$LAST_SUCCESS_FILE"
  exit 0
fi

git diff --cached --check

COMMIT_MESSAGE="Daily LazyInvest research refresh $TODAY"
git commit -m "$COMMIT_MESSAGE"

if [[ "$NO_PUSH" -eq 1 ]]; then
  log "Skipping push because --no-push was set."
else
  git push "$REMOTE" "$BRANCH"
fi

printf '%s\n' "$TODAY" > "$LAST_SUCCESS_FILE"
log "Daily research completed for $TODAY."
