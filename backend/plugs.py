from __future__ import annotations

import configparser
import json
import logging
import re
import threading
from datetime import datetime

from PyP100 import PyP100, MeasureInterval

from config import CONFIG_FILE_PATH, PLUG_STATES_FILE_PATH, config


def human_time_to_seconds(human_time):
    match = re.match(r"(\d+[h|m|s]?)(\d+[h|m|s]?)?(\d+[h|m|s]?)?", human_time)
    if not match:
        return 0
    h = match.group(1)
    hours = int(h.replace('h', '')) if h else 0
    m = match.group(2)
    minutes = int(m.replace('m', '')) if m else 0
    s = match.group(3)
    seconds = int(s.replace('s', '')) if s else 0
    return hours * 3600 + minutes * 60 + seconds


class Plug:
    def __init__(self, plug_config: configparser.SectionProxy, email: str, password: str, enabled: bool = True):
        self.name = plug_config.get('name')
        self.address = plug_config.get('address')
        self.enabled = enabled
        self.tapo = PyP100.Switchable(self.address, email, password)

        periods_temp = {}
        for key, val in plug_config.items():
            m = re.match(r'period(\d+)_(start|end)_hour', key)
            if m:
                idx = int(m.group(1))
                field = 'start_hour' if m.group(2) == 'start' else 'end_hour'
                periods_temp.setdefault(idx, {})[field] = int(val)
            m2 = re.match(r'period(\d+)_runtime_human', key)
            if m2:
                idx = int(m2.group(1))
                periods_temp.setdefault(idx, {})['runtime_human'] = val
        self.periods = []
        for idx in sorted(periods_temp):
            p = periods_temp[idx]
            human = p.get('runtime_human')
            secs = human_time_to_seconds(human) if human else 0
            self.periods.append({
                'start_hour': p.get('start_hour', 0),
                'end_hour': p.get('end_hour', 0),
                'runtime_human': human,
                'runtime_seconds': secs,
                'target': None
            })

    def calculate_target_hours(self, prices: list[tuple[int, float]]):
        if prices:
            for period in self.periods:
                period['target'] = min(
                    [(h, p) for h, p in prices if period['start_hour'] <= h <= period['end_hour']],
                    key=lambda x: x[1]
                )

    def runtime_seconds(self):
        current_hour = datetime.now().hour
        for period in self.periods:
            tgt = period.get('target')
            if tgt and tgt[0] == current_hour:
                return period['runtime_seconds']
        return 0

    def get_rule_remain_seconds(self):
        result = None
        try:
            rules = self.tapo.getCountDownRules()['rule_list']
            if rules:
                rule = next((r for r in rules if r.get("enable")), rules[0])
                enabled = rule.get("enable")
                rem = rule.get("remain")
                if enabled and isinstance(rem, (int, float)) and rem > 0:
                    result = int(rem)
        except Exception as e:
            logging.error(f"Failed to get countdown rules: {e}")
        return result

    def cancel_countdown_rules(self):
        try:
            rules_response = self.tapo.getCountDownRules()
            rules = rules_response.get('rule_list', [])

            # Disable all active rules by setting their 'enable' to 0
            for rule in rules:
                if rule.get('enable', 0) == 1:
                    rule_id = rule.get('id')
                    if rule_id:
                        # Edit the rule to disable it
                        self.tapo.request('edit_countdown_rule', {
                            'id': rule_id,
                            'enable': False,
                            'delay': rule.get('delay', 0),
                            'desired_states': rule.get('desired_states', {'on': False})
                        })
            logging.info(f"Cancelled countdown rules for {self.name}")
        except Exception as e:
            logging.error(f"Failed to cancel countdown rules for {self.name}: {e}")

    def get_hourly_energy(self):
        now = datetime.now()
        day_start = datetime(now.year, now.month, now.day)
        start_ts = int(day_start.timestamp())
        end_ts = int(now.timestamp())
        resp = self.tapo.request("get_energy_data", {"start_timestamp": start_ts, "end_timestamp": end_ts, "interval": MeasureInterval.HOURS.value})
        raw = resp.get('data', [])
        base_ts = resp.get('start_timestamp', start_ts)
        interval_min = resp.get('interval', 60)
        step = interval_min * 60
        out = []
        for i, val in enumerate(raw):
            ts = base_ts + i * step
            hr = datetime.fromtimestamp(ts).hour
            kwh = val / 1000
            out.append({'hour': hr, 'value': kwh})
        return out

    def get_current_power(self):
        try:
            status = self.tapo.request('get_energy_usage')
            if 'current_power' in status:
                return round(status['current_power'] / 1000, 2)
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to get current power: {e}")
            return None


class PlugManager:
    """Manages shared plug instances that are used by both API and manager thread."""

    def __init__(self):
        self._plugs: list[Plug] = []
        self._lock = threading.Lock()

    def reload_plugs(self, enabled_only=False):
        """Reload plugs from config file. Thread-safe."""
        config.read(CONFIG_FILE_PATH)
        tapo_email = config.get('credentials', 'tapo_email')
        tapo_password = config.get('credentials', 'tapo_password')
        new_plugs = []

        for section in config.sections():
            if section.startswith("plug"):
                address = config[section].get('address')
                if not address:
                    continue
                enabled = is_plug_enabled(address)
                if (not enabled_only) or enabled:
                    new_plugs.append(Plug(config[section], tapo_email, tapo_password, enabled))

        with self._lock:
            self._plugs = new_plugs

        logging.info(f"Reloaded {len(new_plugs)} plugs from config")

    def get_plugs(self, enabled_only=False) -> list[Plug]:
        """Get current plugs. Thread-safe read."""
        with self._lock:
            if enabled_only:
                return [p for p in self._plugs if p.enabled]
            return self._plugs.copy()

    def get_plug_by_address(self, address: str) -> Plug | None:
        """Get a specific plug by address. Thread-safe."""
        with self._lock:
            for p in self._plugs:
                if p.address == address:
                    return p
        return None


# Global plug manager instance (shared between API and manager thread)
plug_manager = PlugManager()


def _load_plug_states():
    """Load plug states from JSON file. True = automatic mode enabled, False = manual mode."""
    try:
        with open(PLUG_STATES_FILE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_plug_states(states):
    """Save plug states to JSON file."""
    with open(PLUG_STATES_FILE_PATH, 'w') as f:
        json.dump(states, f, indent=2)


def is_plug_enabled(address: str) -> bool:
    """Check if plug is in automatic mode. True = automatic mode, False = manual mode."""
    states = _load_plug_states()
    return states.get(address, True)


def toggle_plug_enabled(address: str):
    """Toggle plug between automatic and manual mode. Preserves current plug state."""
    states = _load_plug_states()

    plug_exists = False
    for section in config.sections():
        if section.startswith("plug") and config[section].get('address') == address:
            plug_exists = True
            break

    if not plug_exists:
        raise ValueError("Plug not found")

    current = states.get(address, True)
    states[address] = not current
    _save_plug_states(states)


def get_plugs(enabled_only=False) -> list[Plug]:
    """Get plugs from shared plug manager. If enabled_only=True, returns only plugs in automatic mode."""
    return plug_manager.get_plugs(enabled_only)


def get_plug_energy(address):
    p = plug_manager.get_plug_by_address(address)
    if not p:
        raise ValueError(f"Plug with address {address} not found")
    return p.get_hourly_energy()
