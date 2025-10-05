#!/bin/bash

if [ "$#" -lt 3 ] || [ "$#" -gt 6 ]; then
  echo "Usage: $0 <TZ> <CONFIG_PATH> <USER_ID> [CLIENT_PORT] [BACKEND_PORT] [GATEWAY_PORT]"
  echo "Example: $0 Europe/Madrid ./config 1000 3000 3001 3002"
  exit 1
fi

export TZ=$1
export CONFIG_PATH=$2
export USER_ID=$3
export CLIENT_PORT=${4:-3000}
export BACKEND_PORT=${5:-3001}
export GATEWAY_PORT=${6:-3002}

echo "Starting services with the following configuration:"
echo "TZ: $TZ"
echo "CONFIG_PATH: $CONFIG_PATH"
echo "USER_ID: $USER_ID"
echo "CLIENT_PORT: $CLIENT_PORT"
echo "BACKEND_PORT: $BACKEND_PORT"
echo "GATEWAY_PORT: $GATEWAY_PORT"

# bring up the containers with mapped UID/GID and configurable ports
docker-compose up -d --build
