# AGENTS.md

## Commands

**Dev mode (recommended for iteration):** `./dev.sh` (starts manager, API, and frontend, then exits)
- Returns PIDs and log paths in machine-readable format for programmatic control
- Logs are written to `/tmp/energy-manager-dev/` with separate files for each service
- To stop services: `kill $MANAGER_PID $API_PID $FRONTEND_PID`
- Log files: `manager.log`, `api.log`, `frontend.log`, `dev.log`

**Manual dev setup:**
- Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Manager: `python manager.py` (runs price fetching, automatic schedules, scheduled events)
- API: `uvicorn api:app --reload` (handles HTTP requests on port 8000)
- Frontend: `cd client && npm install && npm run dev` (Vite dev server proxies /api to backend)

**Lint:** `cd client && npm run lint`
**Typecheck:** `cd client && npm run build` (build includes typecheck)
**Build frontend:** `cd client && npm run build`
**Docker:** `./run.sh Europe/Madrid /path/to/config /path/to/data 1000 4000`

## Development without Docker

For faster iteration, run services locally instead of Docker:

1. Use `./dev.sh` to start all services (manager, API, frontend)
2. Frontend (Vite) proxies `/api` to backend API at http://localhost:8000
3. Ensure backend config and data directories exist with Tapo credentials and pricing provider config

**Backend components:**
- **Manager** (manager.py): Runs price fetching, sends daily email notifications, generates automatic schedules for enabled plugs, executes scheduled events (turns plugs on/off at specified times)
- **API** (uvicorn api:app): Handles HTTP requests from frontend - manual plug control (on/off/timer), price/energy/schedule queries

**Note:** Running only `uvicorn api:app` works for manual control and reading prices, but you lose automatic schedules and scheduled event execution.

**Testing with Chrome DevTools:**
If Chrome DevTools are available, you can test the application by:
1. Starting dev services with `./dev.sh`
2. Opening http://localhost:5173 in Chrome
3. Using DevTools to inspect network requests, debug JavaScript, and test API interactions

## Testing

No tests currently configured. When adding tests, set up a test framework (pytest for Python, Vitest/Jest for React) and document test commands here.

## Python Code Style

**Organization:** Follow patterns in `backend/api.py` and `backend/manager.py`.

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
