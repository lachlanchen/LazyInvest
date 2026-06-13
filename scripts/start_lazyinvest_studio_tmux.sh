#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/start_lazyinvest_studio_tmux.sh [options]

Starts LazyInvest Studio in a tmux session.

Options:
  --session <name>   tmux session name (default: lazyinvest-studio)
  --host <host>      bind host (default: 127.0.0.1)
  --port <port>      bind port (default: 8788)
  --kill             kill an existing session with the same name first
  --no-attach        start in the background and do not attach
  -h, --help         show this help
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="lazyinvest-studio"
HOST="127.0.0.1"
PORT="8788"
KILL_EXISTING=0
ATTACH=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="${2:-}"; shift 2 ;;
    --host) HOST="${2:-}"; shift 2 ;;
    --port) PORT="${2:-}"; shift 2 ;;
    --kill) KILL_EXISTING=1; shift ;;
    --no-attach) ATTACH=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found." >&2
  exit 1
fi

LOG_DIR="$ROOT_DIR/data/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${SESSION}_$(date +%Y%m%d_%H%M%S).log"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  if [[ "$KILL_EXISTING" -eq 1 ]]; then
    tmux kill-session -t "$SESSION"
  else
    echo "tmux session already running: $SESSION"
    echo "attach: tmux attach -t $SESSION"
    if [[ "$ATTACH" -eq 1 ]]; then
      exec tmux attach -t "$SESSION"
    fi
    exit 0
  fi
fi

runner="cd \"$ROOT_DIR\" && set -euo pipefail; python3 scripts/lazyinvest_studio.py --host \"$HOST\" --port \"$PORT\" 2>&1 | tee -a \"$LOG_PATH\"; status=\${PIPESTATUS[0]}; echo; echo \"lazyinvest-studio exit status: \$status\"; echo \"tmux session kept open for inspection; exit the shell to close it.\"; exec bash"

tmux new-session -d -s "$SESSION" -c "$ROOT_DIR" "$runner"
tmux rename-window -t "$SESSION:0" "lazyinvest"
tmux set-option -t "$SESSION" -g mouse on

echo "tmux session: $SESSION"
echo "url: http://$HOST:$PORT"
echo "log: $LOG_PATH"
echo "attach: tmux attach -t $SESSION"

if [[ "$ATTACH" -eq 1 ]]; then
  exec tmux attach -t "$SESSION"
fi
