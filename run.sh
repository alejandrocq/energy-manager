#!/bin/bash

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
  echo "Usage: $0 <TZ> <CONFIG_PATH> <USER_ID> [GATEWAY_PORT]"
  echo "Example: $0 Europe/Madrid ./config 1000 3000"
  exit 1
fi

export TZ=$1
export CONFIG_PATH=$2
export USER_ID=$3
export GATEWAY_PORT=${6:-4000}

echo "Starting services with the following configuration:"
echo "TZ: $TZ"
echo "CONFIG_PATH: $CONFIG_PATH"
echo "USER_ID: $USER_ID"
echo "GATEWAY_PORT: $GATEWAY_PORT"

# bring up the containers with mapped UID/GID and configurable ports
docker-compose up -d --build
