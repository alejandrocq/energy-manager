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

The backend is organized into focused modules with clear separation of concerns:

**Core Modules:**

- `backend/app.py`: FastAPI REST API with async endpoints
  - Uses ThreadPoolExecutor for synchronous Tapo library calls
  - Manages manager thread lifecycle via FastAPI lifespan events
  - Per-plug locking to prevent concurrent access errors
  - `/api/health` endpoint monitors manager thread status

- `backend/manager.py`: Main orchestration loop (152 lines)
  - Background thread that polls every 30 seconds
  - Coordinates price fetching, schedule generation, and plug control
  - Config hot-reload on file modification
  - Delegates responsibilities to specialized modules

- `backend/config.py`: Configuration and constants (21 lines)
  - Centralized logging setup ("energy_manager" logger)
  - Configuration file parsing
  - Provider factory function

- `backend/plugs.py`: Plug and PlugManager classes (231 lines)
  - Plug class wraps PyP100 Tapo devices with thread-safe locking
  - PlugManager singleton maintains shared plug instances
  - Prevents stale plug state between API and manager thread

- `backend/schedules.py`: Scheduling system (317 lines)
  - User-created scheduled events stored in `data/schedules.json`
  - Automatic schedule generation using strategies
  - Event statuses: pending, completed, cancelled, failed
  - Old events (>7 days) automatically cleaned up

- `backend/scheduling.py`: Strategy pattern for schedule calculation
  - Abstract base class for scheduling strategies
  - PeriodStrategy: Find cheapest hours within time windows
  - ValleyDetectionStrategy: Find valleys for multi-window devices
  - Device profiles: water_heater, radiator, generic
  - Typed strategy data classes for compile-time validation

- `backend/notifications.py`: Email notifications (34 lines)
  - Daily price summary emails
  - Plug action notifications
  - Sends via internal postfix service

- `backend/providers.py`: Price provider abstraction
  - Currently supports OMIE (Spanish electricity market)
  - `@cached_prices` decorator caches results by date
  - Backoff mechanism for temporary failures

**Data Flow:**

1. Manager loads `config.properties` (hot-reloadable, updates shared PlugManager state)
2. Provider fetches daily prices from external API (cached by date)
3. Scheduling strategies calculate target hours for enabled plugs
4. Automatic schedules generated and stored in `data/schedules.json`
5. Manager loop processes pending schedules at target times
6. Plug operations use per-plug locks to prevent concurrent access
7. Email notifications sent via postfix for daily summaries and plug actions

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

**IMPORTANT:** Always use the `./dev.sh` script for local development. This is the standard and only supported way to run the development environment.

The script handles:
- Virtual environment setup and dependencies
- Starting unified backend (API + Manager) on port 8000
- Starting frontend dev server on port 5173
- Process lifecycle management and cleanup
- Logging to `/tmp/energy-manager-dev/*.log`

**Do not run backend or frontend manually** unless you have a specific reason for isolated testing.

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

To stop services: `kill $BACKEND_PID $FRONTEND_PID`

**Testing with Chrome DevTools:**
If Chrome DevTools are available, you can test the application by:
1. Starting dev services with `./dev.sh`
2. Opening http://localhost:5173 in Chrome
3. Using DevTools to inspect network requests, debug JavaScript, and test API interactions

## Git Commit Guidelines

**Commit Message Format:**
- Use concise, descriptive commit messages in imperative mood (e.g., "Add feature" not "Added feature")
- First line should be a summary (50-72 characters)
- **Body is REQUIRED and must use bullet points** (2-5 bullets maximum)
- No signatures or co-author tags unless explicitly requested
- Keep commits focused on a single logical change

**Commit Message Structure:**
- **Summary:** Brief description of what changed (required)
- **Body:** ALWAYS include bullet points explaining the changes (required, 2-5 bullets)
  - Focus on WHAT changed, not why
  - Be concise and specific
  - Each bullet should describe one logical change

**Examples:**

Good commit messages:
```
Refactor backend into focused modules for better organization

- Split manager logic into separate modules
- Extract schedule management to schedules.py
- Create plug manager singleton for shared state

Add countdown timer support for manual plug control

- Add timer endpoint to API with duration validation
- Implement countdown logic in manager loop
- Update frontend with timer selector component
```

Bad commit messages:
```
Fixed stuff

Updated files

- Changed app.py
- Modified manager.py
- Updated schedules.py
- Fixed providers.py
- Refactored plugs.py
- Added new logging format    <-- MORE THAN 5 BULLETS

🤖 Generated with Claude Code <-- DO NOT ADD SIGNATURES

Standardize logging format   <-- NO BODY WITH BULLETS
```

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

The manager runs in a background thread with 30-second intervals:
1. Check config file modification time, reload if changed (updates shared PlugManager)
2. Once per day: fetch prices, generate automatic schedules, send daily email
3. Every iteration: process pending scheduled events (both automatic and manual)
4. Plug operations acquire per-plug locks to prevent concurrent access errors
5. Handle plug errors by reinitializing session
6. Stop gracefully on shutdown signal (via threading.Event)

### Scheduled Events

Both automatic and manual schedules are stored in `data/schedules.json` with statuses:
- `pending`: Not yet executed
- `completed`: Successfully executed
- `cancelled`: User cancelled
- `failed`: Execution error

**Schedule Types:**
- **Automatic:** Generated daily by scheduling strategies based on electricity prices
- **Manual:** User-created via API for specific future times

Old events (>7 days) are automatically cleaned up. Automatic schedules are regenerated daily and old ones are cleared.

### Price Provider Pattern

Providers implement `PricesProvider` abstract class:
- `unavailable()`: Returns True if provider temporarily failed (backoff period)
- `get_prices(target_date)`: Returns list of `(hour, price)` tuples

The `@cached_prices` decorator caches results by date to avoid redundant API calls.

### Scheduling Strategy Pattern

Strategies implement the abstract `SchedulingStrategy` class to calculate optimal plug schedules:

**PeriodStrategy:**
- Finds cheapest hours within configured time windows
- Each period has start/end hours and runtime duration
- Selects the cheapest contiguous block within each period

**ValleyDetectionStrategy:**
- Groups contiguous cheap hours into "valleys"
- Useful for devices needing multiple heating windows (water heaters)
- Device profiles define valley selection criteria
- Prevents overlapping schedules in adjacent hours

**Typed Strategy Data:**
- `PeriodStrategyData`: Configuration for period-based scheduling
- `ValleyDetectionStrategyData`: Configuration for valley detection
- Compile-time validation via dataclasses

## Testing

No tests currently configured. When adding tests, set up a test framework (pytest for Python, Vitest/Jest for React) and document test commands here.

## Python Code Style

**Organization:** Follow the modular architecture established in the backend:
- `app.py`: API endpoints and manager thread lifecycle
- `manager.py`: Orchestration loop only
- `config.py`: Configuration and logging setup
- `plugs.py`: Plug and PlugManager classes
- `schedules.py`: Schedule management and execution
- `scheduling.py`: Strategy pattern for schedule calculation
- `notifications.py`: Email notification functions
- `providers.py`: Price provider abstraction

Keep modules focused on single responsibilities. Avoid circular dependencies.

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
- Abstract base classes: Use ABC for provider and strategy interfaces
- Strategy pattern: Implement `SchedulingStrategy` ABC for schedule calculation
- Singleton pattern: PlugManager maintains single shared plug instances
- Configuration: Use configparser.ConfigParser for .properties files
- Data persistence: JSON for simple data structures (schedules)
- Time zones: Always store datetimes as UTC, convert to local for display
- Thread safety: Use threading.Lock for shared resource access
- Context managers: Use `with` statements for lock acquisition

**Logging:** Use centralized logger: `logger = logging.getLogger("energy_manager")`. The logger is configured in `config.py` and works seamlessly with uvicorn. Use structured format: `MESSAGE [param=value]`

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

## Change Documentation

**CRITICAL:** All important changes, fixes, and improvements MUST be documented in `IMPLEMENTATION.md`.

**What to document:**
- Bug fixes (describe the issue and solution)
- New features or functionality
- Architecture changes or refactoring
- Performance optimizations
- Breaking changes or API modifications
- Security improvements
- Dependency updates that affect behavior

**Documentation format in IMPLEMENTATION.md:**
```markdown
## [Date] - Brief title

**Problem:**
- Description of the issue or requirement

**Solution:**
- What was implemented/changed
- Key technical decisions

**Impact:**
- What this affects (backend, frontend, config, etc.)
- Any breaking changes or migration steps needed
```

**When NOT to document:**
- Trivial typo fixes
- Code formatting or style changes
- Internal refactoring with no external impact
- Documentation updates themselves

Keep `IMPLEMENTATION.md` as a chronological log of significant changes for easier project maintenance and onboarding.

## Important Notes

- **No authentication**: Deploy behind reverse proxy with auth or in protected network
- **Config hot-reload**: Changes to `config.properties` are detected and applied without restart (updates shared PlugManager state)
- **Email via postfix**: Backend always sends emails to internal `postfix` service
- **Tapo local protocol**: Plugs must be on same LAN, uses local API not cloud
- **Gateway port**: Configurable via `GATEWAY_PORT` env var (default: 4000)
- **Time zones**: Container timezone set via `TZ` env var in `run.sh`
- **Thread safety**: Per-plug locking ensures API and manager thread don't corrupt PyP100 session state
- **Shared state**: PlugManager singleton ensures API and manager use same Plug instances
