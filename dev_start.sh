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
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
MAIN_LOG="$LOG_DIR/dev.log"
PID_FILE="$LOG_DIR/pids"

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

# Start unified backend (API + Manager)
echo -e "${GREEN}[1/2] Starting backend (API + Manager)...${NC}" | tee -a "$MAIN_LOG"
cd "$BACKEND_DIR"
python app.py --reload --host 0.0.0.0 --port 8000 >> "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# Start frontend
echo -e "${GREEN}[2/2] Starting frontend (Vite)...${NC}" | tee -a "$MAIN_LOG"
cd "$FRONTEND_DIR"
npm run dev >> "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# Wait for services to initialize
echo "Waiting for services to initialize..." | tee -a "$MAIN_LOG"
sleep 5

# Verify services are running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Backend failed to start${NC}" | tee -a "$MAIN_LOG"
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

# Write PIDs to file for dev_stop.sh
cat > "$PID_FILE" <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
BACKEND_LOG=$BACKEND_LOG
FRONTEND_LOG=$FRONTEND_LOG
MAIN_LOG=$MAIN_LOG
EOF

# Output PIDs and log paths for LLM consumption (machine-readable format)
echo "=== SERVICES STARTED ==="
echo "BACKEND_PID=$BACKEND_PID"
echo "FRONTEND_PID=$FRONTEND_PID"
echo "BACKEND_LOG=$BACKEND_LOG"
echo "FRONTEND_LOG=$FRONTEND_LOG"
echo "MAIN_LOG=$MAIN_LOG"
echo "PID_FILE=$PID_FILE"
echo ""
echo -e "${YELLOW}To stop services, run: ./dev_stop.sh${NC}"
