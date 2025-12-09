#! /usr/bin/bash

source .env

# defaults
: "${WORKERS:=4}"
: "${HOST:=127.0.0.1}"
: "${PORT:=8000}"

SESSION="app"

# Create tmux session (detached)
tmux new-session -d -s "$SESSION"

# Pane 0 (left): cloudflared or warning
if [ -z "${CLOUDFLARE_TOKEN+x}" ]; then
  tmux send-keys -t "$SESSION" "echo 'WARNING: CLOUDFLARE_TOKEN not set, not running cloudflared'; bash" C-m
else
  tmux send-keys -t "$SESSION" \
    "cloudflared tunnel run --token $CLOUDFLARE_TOKEN --url $HOST:$PORT" C-m
fi

# Split window vertically → pane 1 (right)
tmux split-window -h -t "$SESSION"

# Run Uvicorn in pane 1
tmux send-keys -t "$SESSION".1 \
  "uv run uvicorn app.main:app --host $HOST --port $PORT --workers $WORKERS" C-m

# Attach
tmux attach -t "$SESSION"
