#!/bin/bash

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <TZ> <CONFIG_PATH>"
  exit 1
fi

export TZ=$1
export CONFIG_PATH=$2

# bring up the containers with mapped UID/GID
docker-compose up -d --build
