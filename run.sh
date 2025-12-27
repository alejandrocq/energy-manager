#!/bin/bash

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
  echo "Usage: $0 <CONFIG_PATH> <DATA_PATH> <USER_ID> [GATEWAY_PORT]"
  echo "Example: $0 ./config ./data 1000 4000"
  exit 1
fi

export CONFIG_PATH=$1
export DATA_PATH=$2
export USER_ID=$3
export GATEWAY_PORT=${4:-4000}

echo "Starting services with the following configuration:"
echo "CONFIG_PATH: $CONFIG_PATH"
echo "DATA_PATH: $DATA_PATH"
echo "USER_ID: $USER_ID"
echo "GATEWAY_PORT: $GATEWAY_PORT"

# bring up the containers with mapped UID/GID and configurable ports
docker-compose up -d --build
