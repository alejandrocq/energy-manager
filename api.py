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
app.mount('/api/static', StaticFiles(directory='.'), name='static')

@app.get('/api/plugs')
async def plugs():
    out = []
    for p in em.get_plugs():
        try:
            st = p.tapo.get_status()
        except:
            st = None
        tr = p.get_rule_remain_seconds()
        out.append({'name':p.name,'address':p.address,'is_on':st,'timer_remaining':tr})
    return out

@app.get('/api/plugs/{address}/energy')
async def plug_energy(address: str):
    try:
        return em.get_plug_energy(address)
    except StopIteration:
        raise HTTPException(404,'not found')

@app.post('/api/plugs/{address}/on')
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

if __name__=='__main__':
    import uvicorn
    uvicorn.run('api:app',host='0.0.0.0',port=8000,reload=True)
