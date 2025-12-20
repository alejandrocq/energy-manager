#!/usr/bin/env sh
set -e

terminate() {
  echo "Received shutdown signal, terminating processes..."

  if [ -n "$ENERGY_MANAGER_PID" ]; then
    kill -TERM $ENERGY_MANAGER_PID
  fi

  if [ -n "$UVICORN_PID" ]; then
    kill -TERM $UVICORN_PID
  fi

  wait
  echo "All processes terminated, exiting."
  exit 0
}

trap terminate TERM INT

python manager.py &
ENERGY_MANAGER_PID=$!

uvicorn api:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

wait
