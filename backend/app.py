import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_provider
from manager import run_manager_main
from plugs import get_plugs, get_plug_energy, is_plug_enabled, plug_manager, toggle_plug_enabled
from schedules import (
    clear_automatic_schedules,
    create_scheduled_event,
    delete_scheduled_event,
    generate_automatic_schedules,
    get_scheduled_events
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ManagerThread:
    """Manages the background manager thread lifecycle."""

    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()

    def start(self):
        """Start the manager thread."""
        logging.info("Starting manager thread")
        self.thread = threading.Thread(
            target=run_manager_main,
            args=(self.stop_event,),
            daemon=False  # Not daemon - we want clean shutdown
        )
        self.thread.start()

    def stop(self, timeout: float = 10.0):
        """Stop the manager thread gracefully."""
        logging.info("Stopping manager thread")
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                logging.warning(f"Manager thread did not stop within timeout [timeout={timeout}]")
            else:
                logging.info("Manager thread stopped successfully")

    def is_alive(self) -> bool:
        """Check if manager thread is running."""
        return self.thread is not None and self.thread.is_alive()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager - handles startup and shutdown."""
    # Startup
    logging.info("Starting Energy Manager backend")

    # Initialize shared plug manager
    logging.info("Loading plugs from config")
    plug_manager.reload_plugs(enabled_only=False)

    manager_thread = ManagerThread()
    manager_thread.start()

    # Store in app state for access in endpoints
    app.state.manager_thread = manager_thread

    yield

    # Shutdown
    logging.info("Shutting down Energy Manager backend")
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
    prices = await run_in_threadpool(get_provider().get_prices, datetime.now())
    all_schedules = await run_in_threadpool(get_scheduled_events)
    for p in get_plugs():
        try:
            st = await run_in_threadpool(p.tapo.get_status)
            tr = await run_in_threadpool(p.get_rule_remain_seconds)
            p.calculate_target_hours(prices)
            # Fetch current energy usage (instantaneous)
            current_power = await run_in_threadpool(p.get_current_power)
        except:
            st = None
            tr = None
            current_power = None

        # Get schedules for this plug
        schedules = [s for s in all_schedules if s['plug_address'] == p.address]

        out.append({
            'name': p.name,
            'address': p.address,
            'enabled': p.enabled,
            'is_on': st,
            'timer_remaining': tr,
            'schedules': schedules,
            'periods': [
                {
                    'start_hour': per['start_hour'],
                    'end_hour': per['end_hour'],
                    'runtime_human': per['runtime_human'],
                    'target_hour': per['target'][0] if per.get('target') else None,
                    'target_price': per['target'][1] if per.get('target') else None,
                }
                for per in p.periods
            ],
            'current_power': current_power
        })
    return out


@app.get('/api/plugs/{address}/energy')
async def plug_energy(address: str):
    try:
        return await run_in_threadpool(get_plug_energy, address)
    except StopIteration:
        raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/toggle_enable')
async def toggle_enable(address: str):
    try:
        await run_in_threadpool(toggle_plug_enabled, address)

        # Handle schedule management based on new mode
        enabled = await run_in_threadpool(is_plug_enabled, address)
        if enabled:
            # Plug switched to automatic mode - regenerate schedules
            try:
                target_date = datetime.now()
                provider = await run_in_threadpool(get_provider)
                prices = await run_in_threadpool(provider.get_prices, target_date)

                if prices:
                    plugs = await run_in_threadpool(get_plugs, False)
                    await run_in_threadpool(generate_automatic_schedules, plugs, prices, target_date)
            except Exception as e:
                # Log error but don't fail the toggle operation
                logging.warning(f"Failed to regenerate schedules [error={e}]")
        else:
            # Plug switched to manual mode - clear automatic schedules
            try:
                await run_in_threadpool(clear_automatic_schedules, address)
            except Exception as e:
                # Log error but don't fail the toggle operation
                logging.warning(f"Failed to clear schedules [error={e}]")

        return {'status': 'success', 'enabled': enabled}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/plugs/{address}/on')
async def plug_on(address: str):
    p = plug_manager.get_plug_by_address(address)
    if p:
        await run_in_threadpool(p.tapo.turnOn)
        return {'address': address, 'turned_on': True}
    raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/off')
async def plug_off(address: str):
    p = plug_manager.get_plug_by_address(address)
    if p:
        await run_in_threadpool(p.tapo.turnOff)
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
        await run_in_threadpool(p.cancel_countdown_rules)

        if request.desired_state:
            await run_in_threadpool(p.tapo.turnOff)
            await run_in_threadpool(p.tapo.turnOnWithDelay, duration_seconds)
        else:
            await run_in_threadpool(p.tapo.turnOn)
            await run_in_threadpool(p.tapo.turnOffWithDelay, duration_seconds)

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
    data = await run_in_threadpool(get_provider().get_prices, datetime.now())
    return [{'hour': h, 'value': p} for h, p in data]


class ScheduleRequest(BaseModel):
    target_datetime: str  # ISO format datetime string
    desired_state: bool  # True = turn ON, False = turn OFF
    duration_minutes: int | None = None  # Optional duration in minutes


@app.post('/api/plugs/{address}/schedule')
async def create_schedule(address: str, request: ScheduleRequest):
    p = plug_manager.get_plug_by_address(address)
    if p:
        duration_seconds = request.duration_minutes * 60 if request.duration_minutes else None
        event = await run_in_threadpool(
            create_scheduled_event,
            address,
            p.name,
            request.target_datetime,
            request.desired_state,
            duration_seconds
        )
        return event
    raise HTTPException(404, 'Plug not found')


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


@app.post('/api/recalculate_schedules')
async def recalculate_schedules():
    """Force recalculation of automatic schedules based on current prices."""
    try:
        target_date = datetime.now()
        provider = await run_in_threadpool(get_provider)
        prices = await run_in_threadpool(provider.get_prices, target_date)

        if not prices:
            raise HTTPException(500, 'No price data available')

        plugs = await run_in_threadpool(get_plugs, False)
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
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        lifespan="on",
        log_level="info"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Energy Manager Backend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    run_app(host=args.host, port=args.port, reload=args.reload)
