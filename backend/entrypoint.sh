#!/usr/bin/env sh
set -e

terminate() {
  echo "Received shutdown signal, terminating backend process..."

  if [ -n "$BACKEND_PID" ]; then
    kill -TERM $BACKEND_PID
  fi

  wait
  echo "Backend process terminated, exiting."
  exit 0
}

trap terminate TERM INT

python app.py --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

wait
