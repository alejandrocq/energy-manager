import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import energy_manager as em
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

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


@app.get('/api/plugs')
async def plugs():
    out = []
    for p in em.get_plugs():
        try:
            st = await run_in_threadpool(p.tapo.get_status)
            tr = await run_in_threadpool(p.get_rule_remain_seconds)
            prices = await run_in_threadpool(em.get_provider().get_prices, datetime.now())
            p.calculate_target_hours(prices)
        except:
            st = None
            tr = None

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
            ]
        })
    return out


@app.get('/api/plugs/{address}/energy')
async def plug_energy(address: str):
    try:
        return await run_in_threadpool(em.get_plug_energy, address)
    except StopIteration:
        raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/toggle_enable')
async def toggle_enable(address: str):
    try:
        await run_in_threadpool(em.toggle_plug_enabled, address)
        return {'status': 'success'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/plugs/{address}/on')
async def plug_on(address: str):
    for p in em.get_plugs():
        if p.address == address:
            await run_in_threadpool(p.tapo.turnOn)
            return {'address': address, 'turned_on': True}
    raise HTTPException(404, 'not found')


@app.post('/api/plugs/{address}/off')
async def plug_off(address: str):
    for p in em.get_plugs():
        if p.address == address:
            await run_in_threadpool(p.tapo.turnOff)
            return {'address': address, 'turned_off': True}
    raise HTTPException(404, 'not found')


@app.get('/api/prices')
async def get_prices():
    data = await run_in_threadpool(em.get_provider().get_prices, datetime.now())
    return [{'hour': h, 'value': p} for h, p in data]


app.mount("/", StaticFiles(directory="client/dist", html=True, check_dir=False), name="client")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run('api:app', host='0.0.0.0', port=8000, reload=True)
