# AGENTS.md

This file provides comprehensive guidance for working with code in this repository.

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

### Quick Start (Recommended)

```bash
# Single command to start both backend and frontend
./dev.sh
```

This script:
- Creates Python venv in `backend/.venv` if needed
- Installs dependencies automatically
- Starts unified backend (API + Manager) on port 8000
- Starts frontend dev server on port 5173
- Manages process lifecycle and cleanup
- Logs to `/tmp/energy-manager-dev/*.log`
- Returns PIDs and log paths in machine-readable format for programmatic control

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

To stop services: `kill $BACKEND_PID $FRONTEND_PID`

### Backend Development

```bash
# Setup virtual environment
cd backend
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run unified backend (API + Manager)
python app.py --reload

# Run in production mode
python app.py --host 0.0.0.0 --port 8000

# Or run standalone manager (for testing scheduling logic)
python manager.py
```

API runs on http://localhost:8000

**Backend (app.py):**
- Unified entry point that runs both API and Manager in a single process
- **Manager** runs in background thread: price fetching, daily email notifications, automatic schedule generation, scheduled event execution
- **API** runs on uvicorn: handles HTTP requests for manual plug control (on/off/timer), price/energy/schedule queries
- Uses FastAPI lifespan events to start/stop manager thread

**Benefits of unified backend:**
- Single process to manage (one PID)
- Shared in-memory state (no file-based race conditions)
- Easier debugging - all logs in one place
- Better coordination between API and Manager (no concurrent device access issues)

### Frontend Development

```bash
cd client

# Install dependencies
npm install

# Dev server with hot reload
npm run dev

# Lint code
npm run lint

# Typecheck (build includes typecheck)
npm run build

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

### Development without Docker

For faster iteration, run services locally instead of Docker:

1. Use `./dev.sh` to start all services (unified backend, frontend)
2. Frontend (Vite) proxies `/api` to backend API at http://localhost:8000
3. Ensure backend config and data directories exist with Tapo credentials and pricing provider config

**Testing with Chrome DevTools:**
If Chrome DevTools are available, you can test the application by:
1. Starting dev services with `./dev.sh`
2. Opening http://localhost:5173 in Chrome
3. Using DevTools to inspect network requests, debug JavaScript, and test API interactions

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

## Testing

No tests currently configured. When adding tests, set up a test framework (pytest for Python, Vitest/Jest for React) and document test commands here.

## Python Code Style

**Organization:** Follow patterns in `backend/app.py` and `backend/manager.py`.

**Imports:** Standard library → third-party → local modules (alphabetical within each group). Use `from module import` for commonly used items, `import module` for others.

**Type hints:** Use Python 3.9+ syntax (list[Type] not List[Type]). Always type function signatures. Use tuple[int, float] for price data.

**Async/Blocking I/O:** All synchronous Tapo/PyP100 operations must use `run_in_threadpool()` to avoid blocking the async event loop:
```python
executor = ThreadPoolExecutor(max_workers=10)
async def run_in_threadpool(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
```

**API schemas:** Use Pydantic BaseModel for request/response validation:
```python
class TimerRequest(BaseModel):
    duration_minutes: int
    desired_state: bool
```

**Naming:**
- Variables/functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Private helpers: _prefix

**Error handling:**
- Use specific exceptions (StopIteration, ValueError)
- API endpoints: raise HTTPException(404) for not found, HTTPException(500) for server errors
- Wrap external API calls with try/except, log errors with logging module
- Never expose sensitive data in error messages

**Patterns:**
- Decorators: Use functools.wraps for wrapper functions
- Caching: Implement @cached_prices decorator for memoization by date
- Abstract base classes: Use ABC for provider interfaces
- Configuration: Use configparser.ConfigParser for .properties files
- Data persistence: JSON for simple data structures (plug states, schedules)
- Time zones: Always store datetimes as UTC, convert to local for display

**Logging:** Use logging module with INFO level: `logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')`

**Docstrings:** No docstrings for existing functions. Add docstrings only when creating new public functions.

## TypeScript/React Code Style

**Organization:** Follow patterns in `client/src/App.tsx`.

**Imports:** Organize in this order:
1. React (useState, useEffect, etc.)
2. CSS/styling imports
3. Third-party libraries (chart.js, react-chartjs-2)
4. Icons (react-icons)
5. Local components

```typescript
import React, {useCallback, useEffect, useState, useMemo, memo} from 'react'
import './App.css'
import {Bar} from 'react-chartjs-2'
import {FaPlug} from "react-icons/fa";
import {Modal} from "./Modal";
```

**Types:**
- Use `type` for unions/primitives: `type ToastType = 'success' | 'error'`
- Use `interface` for object shapes: `interface Plug { enabled: boolean; name: string; ... }`
- All components must have type annotations: `const App: React.FC = () => { ... }`
- Component props use interface: `interface ModalProps { isOpen: boolean; onClose: () => void; ... }`

**Hooks:**
- `useState<Type>()` with generic for typed state
- `useCallback` for memoized callbacks (include all dependencies)
- `useMemo` for expensive computations
- `memo()` for component-level performance optimization

**Component patterns:**
- Functional components with React.FC
- Props destructuring with type annotations: `({ isOpen, onClose, title, children }: ModalProps) => { ... }`
- Early returns for conditional rendering
- Event handlers: use arrow functions or useCallback to preserve references

**API interactions:**
- Use fetch with async/await
- Check response.ok before parsing JSON
- Use try/except for error handling with user feedback (toasts)

**Styling:**
- TailwindCSS 4.x utility classes
- Use camelCase for style properties in inline styles
- Responsive design: `flex-col md:flex-row`
- Accessibility: aria-label for buttons, proper semantic HTML

**State management:**
- Local state with useState
- Track pending operations with Record<string, boolean>
- Use object keys for operation tracking: `pendingOperations['toggle-${address}']`

**Logging/Error handling:**
- User-facing errors via toast notifications
- Console errors for debugging
- Graceful degradation for missing data (null checks)

**Naming:**
- Variables/functions: camelCase
- Components/interfaces: PascalCase
- Constants: UPPER_SNAKE_CASE
- Types/interfaces: PascalCase

## Error Handling

**Backend:**
- Try/except with specific exceptions
- HTTPException for API responses (404 not found, 500 errors)
- Log all errors with context
- Never crash on individual plug failures (catch and return None/default)

**Frontend:**
- Check response.ok before JSON.parse()
- Show user feedback via toast notifications
- Handle missing/null data gracefully
- Set loading states during async operations

## Important Notes

- **No authentication**: Deploy behind reverse proxy with auth or in protected network
- **Config hot-reload**: Changes to `config.properties` are detected and applied without restart
- **Email via postfix**: Backend always sends emails to internal `postfix` service
- **Tapo local protocol**: Plugs must be on same LAN, uses local API not cloud
- **Gateway port**: Configurable via `GATEWAY_PORT` env var (default: 4000)
- **Time zones**: Container timezone set via `TZ` env var in `run.sh`
