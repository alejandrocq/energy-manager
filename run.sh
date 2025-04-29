#!/bin/bash

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <TZ> <CONFIG_PATH> <USERNAME> <GROUPNAME>"
  exit 1
fi

export TZ=$1
export CONFIG_PATH=$2

# resolve host UID and GID for given user and group
userInput="$3"
groupInput="$4"
USER_ID=$(id -u "$userInput" 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "User '$userInput' not found"
  exit 1
fi
GROUP_ID=$(getent group "$groupInput" | cut -d: -f3)
if [ -z $GROUP_ID ]; then
  echo "Group '$groupInput' not found"
  exit 1
fi

export USER_ID
export GROUP_ID

# bring up the containers with mapped UID/GID
docker-compose up -d --build
