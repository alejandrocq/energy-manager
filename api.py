from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import energy_manager as em

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)

@app.get('/api/plugs')
async def plugs():
    out = []
    for p in em.get_plugs():
        try:
            st = p.tapo.get_status()
        except:
            st = None

        tr = p.get_rule_remain_seconds()

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
        return em.get_plug_energy(address)
    except StopIteration:
        raise HTTPException(404,'not found')

@app.post('/api/plugs/{address}/toggle_enable')
async def toggle_enable(address: str):
    try:
        em.toggle_plug_enabled(address)
        return {'status': 'success'}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def plug_on(address: str):
    for p in em.get_plugs():
        if p.address==address:
            p.tapo.turnOn()
            return {'address':address,'turned_on':True}
    raise HTTPException(404,'not found')

@app.post('/api/plugs/{address}/off')
async def plug_off(address: str):
    for p in em.get_plugs():
        if p.address==address:
            p.tapo.turnOff()
            return {'address':address,'turned_off':True}
    raise HTTPException(404,'not found')

@app.get('/api/prices')
async def get_prices():
    data = em.provider.get_prices(datetime.now())
    return [{'hour': h, 'value': p} for h, p in data]

app.mount("/", StaticFiles(directory="client/dist", html=True, check_dir=False), name="client")

if __name__=='__main__':
    import uvicorn
    uvicorn.run('api:app',host='0.0.0.0',port=8000,reload=True)
