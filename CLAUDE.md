# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Energy Manager is an intelligent energy-saving application that schedules Tapo smart plugs based on electricity prices. The system automatically fetches daily electricity prices, calculates optimal runtime schedules, and controls smart plugs via their local API.

## Architecture

### Multi-Container Deployment

The application uses a **gateway pattern** with four Docker services:

1. **gateway** (nginx): Single entry point on port 4000 (configurable via `GATEWAY_PORT`)
   - Routes `/api/*` → backend:8000
   - Routes `/*` → client:3000
   - Configuration: `gateway/nginx.conf`

2. **backend** (FastAPI + Python): REST API and scheduling engine
   - Exposes REST endpoints at `/api/*`
   - Runs background manager loop for plug control
   - Mounts config directory via bind-mount
   - Mounts data directory via bind-mount for persistent storage

3. **client** (Vite + React): Web UI
   - Static serving via Vite's preview mode in container
   - TailwindCSS 4.x with Vite plugin
   - Chart.js for energy usage visualization

4. **postfix**: Internal SMTP relay
   - Used by backend for email notifications
   - No external ports exposed

### Backend Architecture

**Core Components:**

- `backend/app.py`: FastAPI REST API with async endpoints using ThreadPoolExecutor for Tapo library calls (synchronous)
- `backend/manager.py`: Main scheduling engine and plug management
  - Background loop polls every 30 seconds
  - Handles price fetching, schedule calculation, plug control, and scheduled events
  - Config hot-reload on file modification
  - Persistent scheduled events in `data/schedules.json`
- `backend/providers.py`: Price provider abstraction with caching decorator
  - Currently supports OMIE (Spanish electricity market)
  - Cached results by date to avoid redundant API calls

**Data Flow:**

1. Manager loads `config.properties` (hot-reloadable)
2. Provider fetches daily prices from external API
3. For each enabled plug, manager calculates cheapest hours within configured periods
4. At target hours, plugs are turned on with countdown timers
5. Email notifications sent via postfix for daily summaries and plug actions
6. User-created schedules stored in `data/schedules.json` and processed by manager loop

**Plug Control:**

- Uses PyP100 library (Tapo P100 protocol)
- Supports countdown rules (turn on/off after delay)
- Energy monitoring: instantaneous power (`current_power`) and hourly energy usage
- Manual override via API does not disable automated scheduling

### Frontend Architecture

**Stack:**

- React 19 with TypeScript
- Vite 6.x for dev server and build
- TailwindCSS 4.x (newer Vite plugin approach)
- Chart.js via react-chartjs-2 for energy charts
- react-icons for UI icons

**Components:**

- `App.tsx`: Main component with plug cards and price display
- `Modal.tsx`: Generic modal wrapper
- `TimerSelector.tsx`: Set countdown timers for plugs
- `ScheduleSelector.tsx`: Create future scheduled events

**API Integration:**

- Development: Vite proxy forwards `/api` → `http://localhost:8000`
- Production: Gateway nginx routes `/api` → backend service

## Development Commands

### Backend Development

```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run unified backend (API + Manager)
python app.py --reload

# Or run standalone manager (for testing scheduling logic)
python manager.py
```

API runs on http://localhost:8000

### Frontend Development

```bash
cd client

# Install dependencies
npm install

# Dev server with hot reload
npm run dev

# Lint code
npm run lint

# Production build (outputs to client/dist)
npm run build
```

Dev server runs on http://localhost:5173 with `/api` proxied to backend.

### Docker Development

```bash
# Start all services (requires config and data directories)
./run.sh Europe/Madrid /path/to/config /path/to/data 1000 4000

# Rebuild without cache
docker-compose build --no-cache

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access via http://localhost:4000 (or custom `GATEWAY_PORT`)

## Configuration

The backend requires two directories bind-mounted in the container:
- `config.properties` in `/app/config/` for configuration
- `data/` in `/app/data/` for persistent storage (schedules, etc.)

See README.md for full config format.

Key sections:
- `[settings]`: `provider` (currently only "omie" supported)
- `[email]`: Email addresses for notifications
- `[credentials]`: Tapo account credentials
- `[plug1]`, `[plug2]`, etc.: Per-plug configuration with periods and runtime

The `enabled` field can be toggled via API (`POST /api/plugs/{address}/toggle_enable`) and is persisted to config file.

## API Endpoints

**Plugs:**
- `GET /api/plugs` - List all plugs with status, schedules, and current power
- `POST /api/plugs/{address}/on` - Turn plug on
- `POST /api/plugs/{address}/off` - Turn plug off
- `POST /api/plugs/{address}/toggle_enable` - Toggle plug enabled state (persists to config)
- `POST /api/plugs/{address}/timer` - Set countdown timer (body: `{duration_minutes, desired_state}`)
- `GET /api/plugs/{address}/energy` - Get hourly energy usage for today

**Schedules:**
- `POST /api/plugs/{address}/schedule` - Create scheduled event (body: `{target_datetime, duration_minutes?}`)
- `GET /api/plugs/{address}/schedules` - Get pending schedules for plug
- `DELETE /api/plugs/{address}/schedules/{schedule_id}` - Cancel scheduled event

**Prices:**
- `GET /api/prices` - Get today's hourly electricity prices

## Key Implementation Details

### Async + ThreadPoolExecutor Pattern

The API uses `asyncio` with `ThreadPoolExecutor` because the PyP100 Tapo library is synchronous. All Tapo operations are wrapped in `run_in_threadpool()` to avoid blocking the async event loop.

### Manager Loop Logic

The manager runs an infinite loop with 30-second intervals:
1. Check config file modification time, reload if changed
2. Once per day: fetch prices, calculate schedules, send daily email
3. Every iteration: check if current hour matches target hour for any plug → turn on with timer
4. Every iteration: process pending scheduled events
5. Handle plug errors by reinitializing session

### Scheduled Events

User-created schedules are stored in `data/schedules.json` with statuses:
- `pending`: Not yet executed
- `completed`: Successfully executed
- `cancelled`: User cancelled
- `failed`: Execution error

Old events (>7 days) are automatically cleaned up.

### Price Provider Pattern

Providers implement `PricesProvider` abstract class:
- `unavailable()`: Returns True if provider temporarily failed (backoff period)
- `get_prices(target_date)`: Returns list of `(hour, price)` tuples

The `@cached_prices` decorator caches results by date to avoid redundant API calls.

## Important Notes

- **No authentication**: Deploy behind reverse proxy with auth or in protected network
- **Config hot-reload**: Changes to `config.properties` are detected and applied without restart
- **Email via postfix**: Backend always sends emails to internal `postfix` service
- **Tapo local protocol**: Plugs must be on same LAN, uses local API not cloud
- **Gateway port**: Configurable via `GATEWAY_PORT` env var (default: 4000)
- **Time zones**: Container timezone set via `TZ` env var in `run.sh`
