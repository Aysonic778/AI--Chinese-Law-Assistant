#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMUX_CONF="${TMUX_CONF:-/exec-daemon/tmux.portal.conf}"
tmux_cmd() {
  if [ -f "$TMUX_CONF" ]; then
    tmux -f "$TMUX_CONF" "$@"
  else
    tmux "$@"
  fi
}

start_session() {
  local name="$1"
  local dir="$2"
  local command="$3"
  if ! tmux_cmd has-session -t "=$name" 2>/dev/null; then
    tmux_cmd new-session -d -s "$name" -c "$dir" -- "${SHELL:-bash}" -l
  fi
  tmux_cmd send-keys -t "$name:0.0" C-c 2>/dev/null || true
  sleep 1
  tmux_cmd send-keys -t "$name:0.0" "$command" C-m
}

echo "Starting backend on :8000 ..."
start_session "backend-api" "$ROOT" "cd $ROOT && python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

echo "Starting frontend on :3000 ..."
start_session "frontend-dev" "$ROOT/frontend" "cd $ROOT/frontend && npm run dev -- --hostname 0.0.0.0 --port 3000"

for _ in $(seq 1 20); do
  if curl -sf http://127.0.0.1:3000 >/dev/null && curl -sf http://127.0.0.1:8000/api/health >/dev/null; then
    echo ""
    echo "Ready:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000/api/health"
    echo ""
    echo "Cursor Cloud 预览若显示 Disconnected，请点击预览页上的 Reconnect，"
    echo "或在 Ports 面板重新打开 3000 端口。"
    exit 0
  fi
  sleep 1
done

echo "Services started but health check timed out. Check tmux sessions: backend-api, frontend-dev"
exit 1
