#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PID_FILE="/tmp/energy-manager-dev/pids"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}Error: PID file not found at $PID_FILE${NC}"
    echo "Services may not be running, or were started manually."
    exit 1
fi

# Read PIDs from file
source "$PID_FILE"

echo -e "${YELLOW}Stopping Energy Manager development services...${NC}"

# Function to stop a process safely
stop_process() {
    local pid=$1
    local name=$2

    if [ -z "$pid" ]; then
        echo -e "${YELLOW}No PID found for $name${NC}"
        return
    fi

    # Check if process is running
    if ! kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}$name (PID $pid) is not running${NC}"
        return
    fi

    echo -e "${GREEN}Stopping $name (PID $pid)...${NC}"
    kill "$pid" 2>/dev/null

    # Wait up to 5 seconds for graceful shutdown
    for i in {1..5}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}$name stopped successfully${NC}"
            return
        fi
        sleep 1
    done

    # Force kill if still running
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}Force killing $name...${NC}"
        kill -9 "$pid" 2>/dev/null
        sleep 1
        if ! kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}$name stopped (forced)${NC}"
        else
            echo -e "${RED}Failed to stop $name${NC}"
        fi
    fi
}

# Stop services
stop_process "$BACKEND_PID" "Backend"
stop_process "$FRONTEND_PID" "Frontend"

# Remove PID file
rm -f "$PID_FILE"

echo ""
echo -e "${GREEN}All services stopped!${NC}"
