#!/bin/bash

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <TZ> <CONFIG_PATH> <USER_ID>"
  exit 1
fi

export TZ=$1
export CONFIG_PATH=$2
export USER_ID=$3

# bring up the containers with mapped UID/GID
docker-compose up -d --build
