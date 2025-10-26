import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import manager as m

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)

executor = ThreadPoolExecutor(max_workers=10)


class TimedTurnOnRequest(BaseModel):
    duration_minutes: int


async def run_in_threadpool(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))


@app.get('/api/plugs')
async def plugs():
    out = []
    prices = await run_in_threadpool(m.get_provider().get_prices, datetime.now())
    for p in m.get_plugs():
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

        out.append({
            'name': p.name,
            'address': p.address,
            'enabled': p.enabled,
            'is_on': st,
            'timer_remaining': tr,
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
        return await run_in_threadpool(m.get_plug_energy, address)
    except StopIteration:
        raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/toggle_enable')
async def toggle_enable(address: str):
    try:
        await run_in_threadpool(m.toggle_plug_enabled, address)
        return {'status': 'success'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/plugs/{address}/on')
async def plug_on(address: str):
    for p in m.get_plugs():
        if p.address == address:
            await run_in_threadpool(p.tapo.turnOn)
            return {'address': address, 'turned_on': True}
    raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/off')
async def plug_off(address: str):
    for p in m.get_plugs():
        if p.address == address:
            await run_in_threadpool(p.tapo.turnOff)
            return {'address': address, 'turned_off': True}
    raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/on_timed')
async def plug_on_timed(address: str, request: TimedTurnOnRequest):
    for p in m.get_plugs():
        if p.address == address:
            duration_seconds = request.duration_minutes * 60
            await run_in_threadpool(p.cancel_countdown_rules)
            await run_in_threadpool(p.tapo.turnOn)
            await run_in_threadpool(p.tapo.turnOffWithDelay, duration_seconds)
            return {
                'address': address,
                'turned_on': True,
                'duration_minutes': request.duration_minutes,
                'duration_seconds': duration_seconds
            }
    raise HTTPException(404, 'not found')


@app.get('/api/prices')
async def get_prices():
    data = await run_in_threadpool(m.get_provider().get_prices, datetime.now())
    return [{'hour': h, 'value': p} for h, p in data]


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('api:app', host='0.0.0.0', port=8000, reload=True)

