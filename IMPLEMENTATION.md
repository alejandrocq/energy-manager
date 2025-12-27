# Implementation Log

This file documents significant changes, fixes, and improvements to the Energy Manager project.

**Note:** Entries are ordered from oldest to newest (top to bottom).

---

## 2025-12-25 - Unify backend to run API and Manager in single process

**Problem:**
- Backend ran as two separate processes (API and Manager)
- Separate Plug instances caused stale state issues
- Difficult to coordinate between API and Manager
- Two PIDs to manage during development

**Solution:**
- Manager runs in background thread within uvicorn process
- FastAPI lifespan events manage manager thread lifecycle
- Shared PlugManager ensures API and Manager use same instances
- Added /api/health endpoint to monitor manager thread
- Config hot-reload updates shared plug instances atomically
- Consolidated into single app.py file

**Impact:**
- Backend: Single process to manage (one PID)
- Shared in-memory state eliminates stale plug instances
- Better coordination between API and Manager
- Simpler deployment and debugging

---

## 2025-12-25 - Consolidate documentation into AGENTS.md

**Problem:**
- Documentation split between CLAUDE.md and AGENTS.md
- Duplication made updates error-prone
- Unclear which file was source of truth

**Solution:**
- Moved all documentation to AGENTS.md
- Replaced CLAUDE.md with @AGENTS.md reference
- Merged architecture, API docs, and code style guidelines

**Impact:**
- Documentation: Single source of truth
- Easier maintenance
- No duplication

---

## 2025-12-26 - Refactor backend into focused modules for better organization

**Problem:**
- Original manager.py was 722 lines handling multiple responsibilities
- Difficult to maintain and test
- No clear separation of concerns

**Solution:**
- Split manager.py into 5 specialized modules
- config.py: Configuration and constants (21 lines)
- plugs.py: Plug and PlugManager classes (231 lines)
- schedules.py: Scheduling system (317 lines)
- notifications.py: Email notifications (34 lines)
- manager.py: Orchestration loop only (152 lines, 79% reduction)

**Impact:**
- Backend: Clear separation of concerns
- No circular dependencies
- Better testability and maintainability
- Each module has single responsibility

---

## 2025-12-26 - Add valley detection scheduling strategy with device profiles

**Problem:**
- Period-based strategy didn't support devices needing multiple heating windows
- Water heaters need morning and evening valleys for optimal energy usage
- No way to prevent overlapping schedules in contiguous cheap hours

**Solution:**
- Implemented strategy pattern for plug scheduling (period, valley_detection)
- Added device profiles: water_heater (dual valleys), radiator, generic
- Group contiguous hours into valleys to prevent overlap
- Removed redundant target calculation from API endpoint

**Impact:**
- Backend: New scheduling strategy available for configuration
- Water heaters can now schedule morning and evening heating optimally
- Better energy optimization for multi-window devices

**Files added:**
- `backend/scheduling.py`: Strategy pattern implementation and device profiles

---

## 2025-12-26 - Replace periods dict with typed strategy data classes

**Problem:**
- Untyped dict structures for strategy data lacked compile-time validation
- Redundant `strategy_config` dict duplicated data in `strategy_data`
- No IDE support or type safety for strategy configurations

**Solution:**
- Created `PeriodStrategyData` and `ValleyDetectionStrategyData` dataclasses
- Removed redundant strategy_config dict
- Strategies now accept typed StrategyData instead of config dicts

**Impact:**
- Backend: Improved type safety and IDE support
- Better compile-time validation
- Cleaner code with less duplication

**Files modified:**
- `backend/scheduling.py`: Added strategy data classes
- Updated strategy implementations to use typed data

---

## 2025-12-26 - Centralize logging configuration to fix uvicorn compatibility

**Problem:**
- Logging setup conflicted with uvicorn's logging configuration
- Duplicate log entries appearing in some contexts
- Inconsistent formatting between API and manager logs

**Solution:**
- Created named logger in config.py ("energy_manager")
- Configured logger to work seamlessly with uvicorn
- All modules now use centralized logger instance

**Impact:**
- Backend: Consistent logging across API and manager thread
- Eliminates duplicate logs
- Better integration with uvicorn's logging system

---

## 2025-12-26 - Fix logger import pattern to prevent stale references

**Problem:**
- Modules captured incomplete logger references during circular imports
- Particularly affected schedules.py when called from manager thread
- Caused logging issues and potential initialization problems

**Solution:**
- Changed all modules to use `logging.getLogger("energy_manager")`
- Removed direct logger imports from config module
- Ensured consistent logger access across all modules

**Impact:**
- Backend: All modules now use proper logger instance
- Fixes logging in manager thread context
- Prevents circular import issues with logging

---

## 2025-12-26 - Add per-plug locking to prevent concurrent access errors

**Problem:**
- Schedules were failing with 403 Forbidden errors
- PyP100 library maintains session state that becomes corrupted with concurrent access
- API endpoints and manager thread accessed same Plug instances simultaneously

**Solution:**
- Added `threading.Lock` to each Plug instance
- Created `run_plug_operation()` helper in app.py for locked API operations
- Wrapped all Tapo operations in lock acquisition
- Used context manager in schedule processing

**Impact:**
- Backend: All Tapo operations now serialize per device
- Eliminates 403 Forbidden errors during concurrent operations
- Allows concurrent operations across different plugs

**Files modified:**
- `backend/plugs.py`: Added `_lock` attribute and `acquire_lock()` method
- `backend/app.py`: Added `run_plug_operation()` and updated all endpoints
- `backend/schedules.py`: Wrapped operations in `with plug.acquire_lock()`

---

## 2025-12-26 - Update documentation standards and commit guidelines

**Problem:**
- No standard file for tracking implementation changes
- Commit message format not strictly defined
- Development environment setup unclear

**Solution:**
- Renamed TODO.md to IMPLEMENTATION.md as change log
- Required bullet points (2-5) in all commit messages
- Mandated use of ./dev.sh for local development
- Added "Change Documentation" section to AGENTS.md

**Impact:**
- Documentation: Clear guidelines for change tracking
- Git: Consistent commit message format
- Development: Standard workflow for all developers

---

## 2025-12-26 - Rename enabled field to automatic_schedules and fix UI state sync

**Problem:**
- Field named "enabled" was ambiguous - didn't clearly represent automatic/manual mode
- UI didn't update correctly after backend reloaded plug_states.json
- In-memory Plug state not updated when toggling automatic/manual mode

**Solution:**
- Renamed "enabled" field to "automatic_schedules" across backend and frontend
- Added update_plug_automatic_state() function to update in-memory state immediately
- Changed toggle_plug_automatic() to return new state value
- Renamed API endpoint from /toggle_enable to /toggle_automatic
- Updated all references in plugs.py, app.py, manager.py, schedules.py, App.tsx

**Impact:**
- Backend: Field name now clearly represents automatic scheduling mode
- Backend: In-memory plug state updated immediately after toggle
- Frontend: UI correctly reflects automatic/manual state after operations
- API: Response field renamed from "enabled" to "automatic_schedules"

**Files modified:**
- backend/config.py: Renamed PLUG_STATES_FILE_PATH variable
- backend/plugs.py: Plug.enabled → Plug.automatic_schedules, added update function
- backend/manager.py: Updated to use renamed field and functions
- backend/app.py: Renamed endpoint and response field, added immediate state update
- backend/schedules.py: Updated to check automatic_schedules field
- client/src/App.tsx: Updated interface and toggle function, renamed API endpoint

---

## 2025-12-27 - Add timezone configuration and enforce timezone-aware datetime handling

**Problem:**
- OMIE electricity prices were being treated as system local time instead of Spanish local time
- System timezone depended on Docker TZ build arg or system defaults
- /etc/timezone reading failed in development (macOS), falling back to UTC
- Mixed naive and timezone-aware datetime calls across codebase
- Schedule times off by 1 hour in winter (CET) and 2 hours in summer (CEST)
- Config periods (2-7, 18-22) expected Spanish local time but were interpreted as system time

**Solution:**
- Added timezone field to config.properties (default: Europe/Madrid)
- Updated config.py to read and validate timezone from config, create ZoneInfo instance
- Removed TZ parameter from run.sh script (no longer needed)
- Removed TZ build arg from docker-compose.yml backend service
- Removed tzdata installation and /etc/timezone setup from backend/Dockerfile
- Converted all datetime.now() calls to timezone-aware:
  - app.py: 3 calls now use datetime.now(TIMEZONE)
  - manager.py: 2 calls now use datetime.now(TIMEZONE)
  - providers.py: 2 calls now use datetime.now(timezone.utc)
  - plugs.py: 3 datetime operations now use timezone-aware datetimes
- Removed /etc/timezone reading from schedules.py, use config.TIMEZONE instead
- OMIE hours now correctly interpreted as configured timezone (e.g., Europe/Madrid)
- All datetimes stored as UTC, but OMIE hour interpretation uses configured timezone

**Impact:**
- Configuration: Timezone explicitly configurable in config.properties
- Docker: Simplified deployment, no TZ environment variables needed
- Development: Works identically in macOS dev and Docker production
- Backend: Consistent timezone-aware datetime handling throughout codebase
- Schedules: OMIE hour 5 (05:00 CET) now correctly creates schedule at 04:00 UTC (winter) or 03:00 UTC (summer)
- Energy data: Hourly energy now uses configured timezone for correct attribution
- Backoff tracking: Provider backoff uses UTC to avoid DST edge cases

**Files modified:**
- backend/config/config.properties: Added timezone field to [settings] section
- backend/config.py: Added TIMEZONE constant with ZoneInfo validation, exported for other modules
- run.sh: Removed TZ parameter and export, updated usage message
- docker-compose.yml: Removed TZ build arg from backend service
- backend/Dockerfile: Removed tzdata, /etc/localtime, and /etc/timezone setup
- backend/app.py: 3 datetime.now() calls → datetime.now(TIMEZONE)
- backend/manager.py: 2 datetime.now() calls → datetime.now(TIMEZONE)
- backend/providers.py: 2 datetime.now() calls → datetime.now(timezone.utc), added timezone import
- backend/plugs.py: 3 datetime operations → timezone-aware (get_hourly_energy, day_start, fromtimestamp)
- backend/schedules.py: Removed /etc/timezone reading, removed ZoneInfo import, 2 tzinfo=local_tz → tzinfo=TIMEZONE

**Testing:**
- Verified schedule generation creates correct UTC times:
  - OMIE hour 5 → 2025-12-27T04:00:00+00:00 (winter CET, correct)
  - OMIE hour 16 → 2025-12-27T15:00:00+00:00 (winter CET, correct)
- Previously generated schedules showed 2025-12-27T05:00:00+00:00 (1 hour off)
- Configuration validated: Europe/Madrid timezone loaded correctly
- Dev environment (macOS): Works without /etc/timezone, uses config timezone