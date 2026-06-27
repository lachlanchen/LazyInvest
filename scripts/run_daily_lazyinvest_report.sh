#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/run_daily_lazyinvest_report.sh [options]

Generates one independent LazyInvest daily research archive in ../LazyInvestReports.
The runner collects public market inputs, asks Codex for a Markdown/TeX/PDF report,
commits the report repository, and pushes it.

Options:
  --date YYYY-MM-DD      report date (default: today in LAZYINVEST_TZ)
  --reports-dir <path>   report repository path (default: ../LazyInvestReports)
  --model <model>        Codex model (default: gpt-5.5)
  --reasoning <level>    reasoning effort: low, medium, high, xhigh (default: xhigh)
  --remote <name>        report repo remote (default: origin)
  --branch <name>        report repo branch (default: current branch or main)
  --dry-run              validate setup and collect inputs; do not run Codex
  --no-push              commit locally but skip git push
  -h, --help             show this help

Environment:
  LAZYINVEST_TZ                         local date timezone (default: Asia/Hong_Kong)
  LAZYINVEST_REPORTS_DIR                default report repository path
  LAZYINVEST_RESEARCH_MODEL             default model override
  LAZYINVEST_RESEARCH_REASONING         default reasoning override
  LAZYINVEST_REPORT_TIMEOUT_SECONDS     max Codex runtime (default: 10800)
  LAZYINVEST_REPORT_EXTRA_INSTRUCTION   appended to the report prompt
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TZ_NAME="${LAZYINVEST_TZ:-Asia/Hong_Kong}"
REPORT_DATE="$(TZ="$TZ_NAME" date +%F)"
YEAR="${REPORT_DATE%%-*}"
REPORTS_DIR="${LAZYINVEST_REPORTS_DIR:-$ROOT_DIR/../LazyInvestReports}"
MODEL="${LAZYINVEST_RESEARCH_MODEL:-gpt-5.5}"
REASONING="${LAZYINVEST_RESEARCH_REASONING:-xhigh}"
REMOTE="${LAZYINVEST_REPORT_REMOTE:-origin}"
BRANCH="${LAZYINVEST_REPORT_BRANCH:-}"
TIMEOUT_SECONDS="${LAZYINVEST_REPORT_TIMEOUT_SECONDS:-10800}"
DRY_RUN=0
NO_PUSH=0

log() {
  printf '[%s] %s\n' "$(TZ="$TZ_NAME" date '+%Y-%m-%d %H:%M:%S %Z')" "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) REPORT_DATE="${2:-}"; YEAR="${REPORT_DATE%%-*}"; shift 2 ;;
    --reports-dir) REPORTS_DIR="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --reasoning) REASONING="${2:-}"; shift 2 ;;
    --remote) REMOTE="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-push) NO_PUSH=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

[[ "$REPORT_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die "Invalid --date: $REPORT_DATE"
YEAR="${REPORT_DATE%%-*}"
[[ "$MODEL" =~ ^[A-Za-z0-9._:-]+$ ]] || die "Invalid model: $MODEL"
case "$REASONING" in
  low|medium|high|xhigh) ;;
  *) die "Invalid reasoning: $REASONING" ;;
esac
[[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || die "Invalid timeout: $TIMEOUT_SECONDS"

command -v git >/dev/null 2>&1 || die "git not found"
command -v codex >/dev/null 2>&1 || die "codex not found"
[[ -d "$REPORTS_DIR" ]] || die "report repository path not found: $REPORTS_DIR"
[[ -d "$REPORTS_DIR/.git" ]] || die "report repository is not initialized: $REPORTS_DIR"

cd "$REPORTS_DIR"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ -z "$BRANCH" ]]; then
  BRANCH="$CURRENT_BRANCH"
fi
if [[ "$BRANCH" == "HEAD" ]]; then
  BRANCH="main"
fi
[[ "$CURRENT_BRANCH" == "$BRANCH" ]] || die "current report branch is $CURRENT_BRANCH, expected $BRANCH"

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  git status --short --untracked-files=all
  die "report repo is dirty before generation; refusing to mix automated changes"
fi

if git remote get-url "$REMOTE" >/dev/null 2>&1; then
  git fetch "$REMOTE" "$BRANCH"
  git pull --ff-only "$REMOTE" "$BRANCH"
fi

RUN_DIR="logs/$YEAR/${REPORT_DATE}_$(date -u +%Y%m%dT%H%M%SZ)"
INPUT_PATH="data/$YEAR/${REPORT_DATE}-market-inputs.json"
MD_PATH="reports/$YEAR/${REPORT_DATE}-lazyinvest-daily-report.md"
TEX_PATH="tex/$YEAR/${REPORT_DATE}-lazyinvest-daily-report.tex"
PDF_PATH="pdf/$YEAR/${REPORT_DATE}-lazyinvest-daily-report.pdf"
PROMPT_PATH="$RUN_DIR/prompt.md"
AGENT_OUTPUT="$RUN_DIR/final.md"
mkdir -p "$RUN_DIR" "data/$YEAR" "reports/$YEAR" "tex/$YEAR" "pdf/$YEAR"

log "Collecting reproducible market input bundle"
python3 "$ROOT_DIR/scripts/collect_daily_market_inputs.py" \
  --date "$REPORT_DATE" \
  --stock-table "$ROOT_DIR/US_Stock_Research_Table_2026-06-13.md" \
  --output "$INPUT_PATH"

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Dry run complete. Input bundle: $REPORTS_DIR/$INPUT_PATH"
  exit 0
fi

cat > "$PROMPT_PATH" <<PROMPT
# LazyInvest Independent Daily Market Report

Today is $REPORT_DATE in $TZ_NAME.

You are the independent daily research backend for LazyInvestReports.
Use Codex $MODEL with reasoning effort $REASONING.

## Mission

Produce a substantial, evidence-linked daily U.S. market and stock research report.
This report must stand alone for the day. Do not merely patch yesterday's prose.

## Required inputs already downloaded

- Public market/macro/SEC input bundle: \`$INPUT_PATH\`
- Source LazyInvest repo: \`$ROOT_DIR\`
- Current watchlist tables:
  - \`$ROOT_DIR/US_Sector_Investment_Matrix_2026-06-13.md\`
  - \`$ROOT_DIR/US_Stock_Research_Table_2026-06-13.md\`
  - \`$ROOT_DIR/US_Underfollowed_Growth_Stocks_2026-06-13.md\`
  - \`$ROOT_DIR/US_Best_Growth_Choice_2026-06-13.md\`

## Research standard

- Use current internet research and command-line tools. Download and inspect source material when it improves evidence quality.
- Prefer primary sources: SEC filings, company investor relations releases/decks, earnings releases, transcripts when available, FRED, Treasury/Federal Reserve data, exchange calendars, and reputable market data.
- Include source links for every major market claim, company result, guidance figure, valuation context, sector claim, and catalyst.
- Preserve GAAP versus non-GAAP distinctions.
- State assumptions visibly. Do not fabricate prices, guidance, filings, or catalysts.
- Mark the report as a research watchlist, not personal financial advice.
- Make a real analytical judgment: market regime, sector setup, risk budget, best single huge-growth choice, evidence for and against, and what would falsify the thesis.
- Include a source log naming the most important downloaded or inspected sources.

## Deliverables

Create or update these files in this repository:

1. \`$MD_PATH\` - high-quality Markdown report.
2. \`$TEX_PATH\` - LaTeX version suitable for PDF compilation.
3. \`$PDF_PATH\` - compiled PDF.
4. \`README.md\` - update the Latest Report links and the report index.

The Markdown report must include:

- Research date and data as-of timestamp.
- Executive summary.
- Market regime dashboard.
- Macro/rates/liquidity section.
- Sector opportunity table with "best investment now", "hot/good", "less noticed/good", "bad to invest", and "less known/high risk" categories.
- Maintained stock table summary.
- Single best huge-growth choice with evidence, proof links, bear case, and falsification checklist.
- Risk register.
- What changed versus prior reports, if a prior report exists.
- Source log and disclaimer.

For PDF compilation, prefer \`scripts/compile_report.sh "$TEX_PATH" "$PDF_PATH"\`.
If compilation fails, fix the TeX and retry. The final state must include a non-empty PDF.

## Validation before final response

- Run \`git diff --check\`.
- Confirm all deliverables exist and the PDF is non-empty.
- Inspect the Markdown for shallow unsupported claims and add citations where needed.
- Do not commit or push; this shell runner commits and pushes after you finish.

Extra operator instruction:
${LAZYINVEST_REPORT_EXTRA_INSTRUCTION:-No extra instruction.}
PROMPT

log "Prompt written to $PROMPT_PATH"
codex_cmd=(
  codex exec
  --ephemeral
  --model "$MODEL"
  -c "model_reasoning_effort=\"$REASONING\""
  --cd "$REPORTS_DIR"
  --output-last-message "$AGENT_OUTPUT"
  --dangerously-bypass-approvals-and-sandbox
  -
)

log "Starting Codex report job"
if command -v timeout >/dev/null 2>&1; then
  timeout "${TIMEOUT_SECONDS}s" "${codex_cmd[@]}" < "$PROMPT_PATH"
else
  "${codex_cmd[@]}" < "$PROMPT_PATH"
fi
log "Codex report job finished. Final response: $AGENT_OUTPUT"

if [[ ! -s "$PDF_PATH" && -x scripts/compile_report.sh && -s "$TEX_PATH" ]]; then
  log "PDF missing after Codex run; compiling from TeX"
  scripts/compile_report.sh "$TEX_PATH" "$PDF_PATH"
fi

[[ -s "$MD_PATH" ]] || die "Markdown report missing or empty: $MD_PATH"
[[ -s "$TEX_PATH" ]] || die "TeX report missing or empty: $TEX_PATH"
[[ -s "$PDF_PATH" ]] || die "PDF report missing or empty: $PDF_PATH"
grep -Eiq "not personal financial advice|research watchlist" "$MD_PATH" || die "report disclaimer missing"
grep -Eiq "source|sources|source log" "$MD_PATH" || die "source section missing"
git diff --check

git add -- README.md AGENTS.md CITATION.cff .github/FUNDING.yml scripts data reports tex pdf

if git diff --cached --quiet; then
  log "No report changes to commit."
  exit 0
fi

git diff --cached --check
git commit -m "Add LazyInvest daily report $REPORT_DATE"

if [[ "$NO_PUSH" -eq 1 ]]; then
  log "Skipping report push because --no-push was set."
else
  git push "$REMOTE" "$BRANCH"
fi

log "Daily report archived for $REPORT_DATE."
