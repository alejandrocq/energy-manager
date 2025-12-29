import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_provider, TIMEZONE

logger = logging.getLogger("uvicorn.error")
from manager import run_manager_main
from plugs import get_plugs, plug_manager, toggle_plug_automatic
from schedules import (
    clear_automatic_schedules,
    create_repeating_schedule,
    create_scheduled_event,
    delete_repeating_schedule,
    delete_scheduled_event,
    generate_automatic_schedules,
    get_scheduled_events
)


class ManagerThread:
    """Manages the background manager thread lifecycle."""

    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()

    def start(self):
        """Start the manager thread."""
        logger.info("Starting manager thread")
        self.thread = threading.Thread(
            target=run_manager_main,
            args=(self.stop_event,),
            daemon=False  # Not daemon - we want clean shutdown
        )
        self.thread.start()

    def stop(self, timeout: float = 10.0):
        """Stop the manager thread gracefully."""
        logger.info("Stopping manager thread")
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                logger.warning(f"Manager thread did not stop within timeout [timeout={timeout}]")
            else:
                logger.info("Manager thread stopped successfully")

    def is_alive(self) -> bool:
        """Check if manager thread is running."""
        return self.thread is not None and self.thread.is_alive()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager - handles startup and shutdown."""
    # Startup
    logger.info("Starting Energy Manager backend")

    manager_thread = ManagerThread()
    manager_thread.start()

    # Store in app state for access in endpoints
    app.state.manager_thread = manager_thread

    yield

    # Shutdown
    logger.info("Shutting down Energy Manager backend")
    manager_thread.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)

executor = ThreadPoolExecutor(max_workers=10)


async def run_in_threadpool(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))


async def run_plug_operation(plug, func, *args, **kwargs):
    """Run a plug operation with locking to prevent concurrent access."""
    def locked_operation():
        with plug.acquire_lock():
            return func(*args, **kwargs)
    return await run_in_threadpool(locked_operation)


@app.get('/api/health')
async def health():
    """Health check endpoint - verifies API and manager thread are running."""
    manager_status = "running" if app.state.manager_thread.is_alive() else "stopped"
    return {
        'status': 'ok' if manager_status == "running" else 'degraded',
        'api': 'running',
        'manager_thread': manager_status
    }


@app.get('/api/plugs')
async def plugs():
    out = []
    all_schedules = await run_in_threadpool(get_scheduled_events)
    for p in get_plugs():
        try:
            def get_plug_status():
                return (
                    p.get_status(),
                    p.get_rule_remain_seconds(),
                    p.get_current_power()
                )
            st, tr, current_power = await run_plug_operation(p, get_plug_status)
        except Exception as e:
            logger.error(f"Failed to get plug status [plug_name={p.name}, address={p.address}, error={type(e).__name__}: {e}]")
            st = None
            tr = None
            current_power = None

        # Get schedules for this plug
        schedules = [s for s in all_schedules if s['plug_address'] == p.address]

        out.append({
            'name': p.name,
            'address': p.address,
            'automatic_schedules': p.automatic_schedules,
            'is_on': st,
            'timer_remaining': tr,
            'schedules': schedules,
            'current_power': current_power
        })
    return out


@app.get('/api/plugs/{address}/energy')
async def plug_energy(address: str):
    p = plug_manager.get_plug_by_address(address)
    if not p:
        raise HTTPException(404, 'not found')
    try:
        return await run_plug_operation(p, p.get_hourly_energy)
    except Exception:
        raise HTTPException(500, 'error fetching energy data')


@app.post('/api/plugs/{address}/toggle_automatic')
async def toggle_automatic(address: str):
    try:
        automatic = await run_in_threadpool(toggle_plug_automatic, address)

        # Handle schedule management based on new mode
        if automatic:
            # Plug switched to automatic mode - regenerate schedules
            try:
                target_date = datetime.now(TIMEZONE)
                provider = await run_in_threadpool(get_provider)
                prices = await run_in_threadpool(provider.get_prices, target_date)

                if prices:
                    plugs = await run_in_threadpool(get_plugs, automatic_only=False)
                    await run_in_threadpool(generate_automatic_schedules, plugs, prices, target_date)
            except Exception as e:
                # Log error but don't fail the toggle operation
                logger.warning(f"Failed to regenerate schedules [error={e}]")
        else:
            # Plug switched to manual mode - clear automatic schedules
            try:
                await run_in_threadpool(clear_automatic_schedules, address)
            except Exception as e:
                # Log error but don't fail the toggle operation
                logger.warning(f"Failed to clear schedules [error={e}]")

        return {'status': 'success', 'automatic_schedules': automatic}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/plugs/{address}/on')
async def plug_on(address: str):
    p = plug_manager.get_plug_by_address(address)
    if p:
        await run_plug_operation(p, p.turn_on)
        return {'address': address, 'turned_on': True}
    raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/off')
async def plug_off(address: str):
    p = plug_manager.get_plug_by_address(address)
    if p:
        await run_plug_operation(p, p.turn_off)
        return {'address': address, 'turned_off': True}
    raise HTTPException(404, 'not found')


class TimerRequest(BaseModel):
    duration_minutes: int
    desired_state: bool  # True for ON, False for OFF


@app.post('/api/plugs/{address}/timer')
async def plug_timer(address: str, request: TimerRequest):
    p = plug_manager.get_plug_by_address(address)
    if p:
        duration_seconds = request.duration_minutes * 60

        def set_timer():
            p.cancel_countdown_rules()
            if request.desired_state:
                p.turn_off()
                p.turn_on_with_delay(duration_seconds)
            else:
                p.turn_on()
                p.turn_off_with_delay(duration_seconds)

        await run_plug_operation(p, set_timer)

        return {
            'address': address,
            'current_state': not request.desired_state,
            'desired_state': request.desired_state,
            'duration_minutes': request.duration_minutes,
            'duration_seconds': duration_seconds
        }
    raise HTTPException(404, 'not found')


@app.get('/api/prices')
async def get_prices():
    data = await run_in_threadpool(get_provider().get_prices, datetime.now(TIMEZONE))
    return [{'hour': h, 'value': p} for h, p in data]


class RecurrenceConfig(BaseModel):
    frequency: Literal['daily', 'weekly', 'monthly', 'custom']
    interval: int = 1
    days_of_week: list[int] | None = None  # 0=Monday, 6=Sunday
    days_of_month: list[int] | None = None  # 1-31
    time: str  # HH:MM format
    end_date: str | None = None  # Optional ISO format date


class ScheduleRequest(BaseModel):
    target_datetime: str | None = None  # ISO format datetime string (required for one-time)
    desired_state: bool  # True = turn ON, False = turn OFF
    duration_minutes: int | None = None  # Optional duration in minutes
    recurrence: RecurrenceConfig | None = None  # For repeating schedules


@app.post('/api/plugs/{address}/schedule')
async def create_schedule(address: str, request: ScheduleRequest):
    p = plug_manager.get_plug_by_address(address)
    if not p:
        raise HTTPException(404, 'Plug not found')

    duration_seconds = request.duration_minutes * 60 if request.duration_minutes else None

    if request.recurrence:
        # Create repeating schedule
        recurrence_dict = {
            'frequency': request.recurrence.frequency,
            'interval': request.recurrence.interval,
            'days_of_week': request.recurrence.days_of_week,
            'days_of_month': request.recurrence.days_of_month,
            'time': request.recurrence.time,
            'end_date': request.recurrence.end_date
        }
        event = await run_in_threadpool(
            create_repeating_schedule,
            address,
            p.name,
            recurrence_dict,
            request.desired_state,
            duration_seconds
        )
        if event is None:
            raise HTTPException(400, 'Invalid recurrence configuration')
        return event
    else:
        # Create one-time schedule
        if not request.target_datetime:
            raise HTTPException(400, 'target_datetime is required for one-time schedules')
        event = await run_in_threadpool(
            create_scheduled_event,
            address,
            p.name,
            request.target_datetime,
            request.desired_state,
            duration_seconds
        )
        return event


@app.get('/api/plugs/{address}/schedules')
async def get_schedules(address: str):
    schedules = await run_in_threadpool(get_scheduled_events, address)
    return schedules


@app.delete('/api/plugs/{address}/schedules/{schedule_id}')
async def delete_schedule(address: str, schedule_id: str):
    deleted = await run_in_threadpool(delete_scheduled_event, schedule_id)
    if deleted:
        return {'status': 'success', 'schedule_id': schedule_id}
    raise HTTPException(404, 'Schedule not found')


@app.delete('/api/plugs/{address}/repeating-schedules/{parent_id}')
async def delete_repeating(address: str, parent_id: str):
    """Cancel all pending events for a repeating schedule series."""
    deleted = await run_in_threadpool(delete_repeating_schedule, parent_id)
    if deleted:
        return {'status': 'success', 'parent_id': parent_id}
    raise HTTPException(404, 'Repeating schedule not found')


@app.post('/api/recalculate_schedules')
async def recalculate_schedules():
    """Force recalculation of automatic schedules based on current prices."""
    try:
        target_date = datetime.now(TIMEZONE)
        provider = await run_in_threadpool(get_provider)
        prices = await run_in_threadpool(provider.get_prices, target_date)

        if not prices:
            raise HTTPException(500, 'No price data available')

        plugs = await run_in_threadpool(get_plugs, automatic_only=False)
        await run_in_threadpool(generate_automatic_schedules, plugs, prices, target_date)

        return {
            'status': 'success',
            'message': f'Automatic schedules recalculated for {target_date.date()}',
            'schedules_count': len(await run_in_threadpool(get_scheduled_events))
        }
    except Exception as e:
        raise HTTPException(500, f'Failed to recalculate schedules: {str(e)}')


def run_app(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the unified backend (API + Manager) in a single process."""
    import uvicorn
    from logging_config import LOGGING_CONFIG

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        lifespan="on",
        log_config=LOGGING_CONFIG
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Energy Manager Backend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    run_app(host=args.host, port=args.port, reload=args.reload)
