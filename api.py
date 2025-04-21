from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import configparser
import logging

from energy_manager import Plug

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/static", StaticFiles(directory="."), name="static")

config = configparser.ConfigParser()
config.read("config.properties")

tapo_email    = config.get("credentials", "tapo_email")
tapo_password = config.get("credentials", "tapo_password")

plugs = []
for section in config.sections():
    if section.startswith("plug") and config[section].getboolean("enabled"):
        plugs.append(Plug(config[section], tapo_email, tapo_password))


@app.get("/api/plugs")
async def list_plugs():
    """
    Return list of plugs with:
      - name
      - address
      - is_on (True/False/None)
      - timer_remaining (seconds or null)
    """
    out = []
    for plug in plugs:
        # 1) read on/off status
        try:
            status = plug.tapo.get_status()
        except Exception:
            logging.exception("Error reading status for %s", plug.name)
            status = None

        # 2) read countdown rules for remaining seconds
        timer = None
        try:
            rules = plug.tapo.getCountDownRules()['rule_list']

            if rules:
                # pick an enabled rule if any
                rule = next((r for r in rules if r.get("enable")), rules[0])
                enabled = rule.get("enable")
                rem = rule.get("remain")
                if enabled and isinstance(rem, (int, float)) and rem > 0:
                    timer = int(rem)
        except Exception:
            logging.exception("Error reading countdown rules for %s", plug.name)

        out.append({
            "name":            plug.name,
            "address":         plug.address,
            "is_on":           status,
            "timer_remaining": timer,
        })

    return out


@app.post("/api/plugs/{address}/on")
async def turn_on(address: str):
    plug = next((p for p in plugs if p.address == address), None)
    if not plug:
        raise HTTPException(404, "Plug not found")
    try:
        plug.tapo.turnOn()
        return {"address": address, "turned_on": True}
    except Exception as e:
        logging.exception("Failed to turn on %s", address)
        raise HTTPException(500, f"Failed to turn on: {e}")


@app.post("/api/plugs/{address}/off")
async def turn_off(address: str):
    plug = next((p for p in plugs if p.address == address), None)
    if not plug:
        raise HTTPException(404, "Plug not found")
    try:
        plug.tapo.turnOff()
        return {"address": address, "turned_off": True}
    except Exception as e:
        logging.exception("Failed to turn off %s", address)
        raise HTTPException(500, f"Failed to turn off: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
