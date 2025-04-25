#!/usr/bin/env sh
set -e

# start postfix
service postfix start

# launch manager + API
python energy_manager.py &
exec uvicorn api:app --host 0.0.0.0 --port 8000
