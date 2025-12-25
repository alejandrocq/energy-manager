#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/backend" && pwd)"
FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/client" && pwd)"

# Log file setup
LOG_DIR="/tmp/energy-manager-dev"
mkdir -p "$LOG_DIR"
MANAGER_LOG="$LOG_DIR/manager.log"
API_LOG="$LOG_DIR/api.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
MAIN_LOG="$LOG_DIR/dev.log"

# Check if virtual environment exists
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}" | tee -a "$MAIN_LOG"
    cd "$BACKEND_DIR"
    python3 -m venv .venv
fi

# Activate virtual environment
source "$BACKEND_DIR/.venv/bin/activate"

# Install dependencies if needed
cd "$BACKEND_DIR"
if ! pip show -q fastapi; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}" | tee -a "$MAIN_LOG"
    pip install -r requirements.txt >> "$MAIN_LOG" 2>&1
fi

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}" | tee -a "$MAIN_LOG"
    cd "$FRONTEND_DIR"
    npm install >> "$MAIN_LOG" 2>&1
fi

# Kill any existing processes on ports before starting
kill_existing() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Killing existing process on port $port (PID: $pid)...${NC}" | tee -a "$MAIN_LOG"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

kill_existing 8000
kill_existing 5173

echo -e "${GREEN}Starting Energy Manager in development mode...${NC}" | tee -a "$MAIN_LOG"

# Start manager
echo -e "${GREEN}[1/3] Starting manager...${NC}" | tee -a "$MAIN_LOG"
cd "$BACKEND_DIR"
python manager.py >> "$MANAGER_LOG" 2>&1 &
MANAGER_PID=$!

# Start API
echo -e "${GREEN}[2/3] Starting API server (uvicorn)...${NC}" | tee -a "$MAIN_LOG"
cd "$BACKEND_DIR"
uvicorn api:app --reload --host 0.0.0.0 --port 8000 >> "$API_LOG" 2>&1 &
API_PID=$!

# Start frontend
echo -e "${GREEN}[3/3] Starting frontend (Vite)...${NC}" | tee -a "$MAIN_LOG"
cd "$FRONTEND_DIR"
npm run dev >> "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# Wait for services to initialize
echo "Waiting for services to initialize..." | tee -a "$MAIN_LOG"
sleep 5

# Verify services are running
if ! kill -0 $MANAGER_PID 2>/dev/null; then
    echo -e "${RED}Error: Manager failed to start${NC}" | tee -a "$MAIN_LOG"
    exit 1
fi

if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}Error: API failed to start${NC}" | tee -a "$MAIN_LOG"
    exit 1
fi

if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Frontend failed to start${NC}" | tee -a "$MAIN_LOG"
    exit 1
fi

echo "" | tee -a "$MAIN_LOG"
echo -e "${GREEN}All services started successfully!${NC}" | tee -a "$MAIN_LOG"
echo "  Frontend: http://localhost:5173"
echo "  Backend API: http://localhost:8000"
echo ""

# Output PIDs and log paths for LLM consumption (machine-readable format)
echo "=== SERVICES STARTED ==="
echo "MANAGER_PID=$MANAGER_PID"
echo "API_PID=$API_PID"
echo "FRONTEND_PID=$FRONTEND_PID"
echo "MANAGER_LOG=$MANAGER_LOG"
echo "API_LOG=$API_LOG"
echo "FRONTEND_LOG=$FRONTEND_LOG"
echo "MAIN_LOG=$MAIN_LOG"
