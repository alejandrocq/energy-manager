from __future__ import annotations

import configparser
import json
import logging
import re
import threading
from datetime import datetime

from PyP100 import PyP100, MeasureInterval

from config import CONFIG_FILE_PATH, PLUG_STATES_FILE_PATH, config

# Get centralized logger (configured in config.py)
logger = logging.getLogger("energy_manager")
from scheduling import (
    create_strategy,
    PeriodConfig,
    PeriodStrategyData,
    ValleyDetectionStrategyData,
)


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
    def __init__(self, plug_config: configparser.SectionProxy, email: str, password: str, automatic_schedules: bool = True):
        self.name = plug_config.get('name')
        self.address = plug_config.get('address')
        self.automatic_schedules = automatic_schedules
        self.tapo = PyP100.Switchable(self.address, email, password)
        self._lock = threading.Lock()

        # Load scheduling strategy (default to 'period' for backward compatibility)
        strategy_name = plug_config.get('strategy', 'period')
        self.strategy = create_strategy(strategy_name)
        self.strategy_name = strategy_name

        # Parse strategy-specific configuration
        if strategy_name == 'valley_detection':
            self._parse_valley_detection_config(plug_config)
        else:
            # Default to period strategy (existing behavior)
            self._parse_period_config(plug_config)

    def acquire_lock(self):
        """Context manager for thread-safe plug operations."""
        return self._lock

    def _parse_period_config(self, plug_config: configparser.SectionProxy):
        """Parse period-based strategy configuration."""
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

        periods: list[PeriodConfig] = []
        for idx in sorted(periods_temp):
            p = periods_temp[idx]
            human = p.get('runtime_human', '0h')
            secs = human_time_to_seconds(human) if human else 0
            runtime_hours = secs / 3600
            periods.append(PeriodConfig(
                start_hour=p.get('start_hour', 0),
                end_hour=p.get('end_hour', 0),
                runtime_human=human,
                runtime_seconds=secs,
                runtime_hours=runtime_hours,
                target_hour=None,
                target_price=None
            ))

        self.strategy_data = PeriodStrategyData(periods=periods)

    def _parse_valley_detection_config(self, plug_config: configparser.SectionProxy):
        """Parse valley detection strategy configuration."""
        device_profile = plug_config.get('device_profile', 'generic')
        runtime_human = plug_config.get('runtime_hours_human')
        runtime_hours_str = plug_config.get('runtime_hours')

        # Parse runtime (support both human format and hours)
        if runtime_human:
            runtime_seconds = human_time_to_seconds(runtime_human)
            runtime_hours = runtime_seconds / 3600
            runtime_human_final = runtime_human
        elif runtime_hours_str:
            runtime_hours = float(runtime_hours_str)
            runtime_seconds = int(runtime_hours * 3600)
            runtime_human_final = f"{int(runtime_hours)}h"
        else:
            runtime_hours = 1
            runtime_seconds = 3600
            runtime_human_final = "1h"

        time_constraints = plug_config.get('time_constraints')
        morning_window = plug_config.get('morning_window')
        evening_window = plug_config.get('evening_window')

        self.strategy_data = ValleyDetectionStrategyData(
            device_profile=device_profile,
            runtime_human=runtime_human_final,
            runtime_seconds=runtime_seconds,
            runtime_hours=runtime_hours,
            target_hours=[],
            target_prices={},
            time_constraints=time_constraints,
            morning_window=morning_window,
            evening_window=evening_window
        )

    def calculate_target_hours(self, prices: list[tuple[int, float]]):
        """Calculate target hours using the configured strategy."""
        if not prices:
            return

        # Use strategy to calculate target hours
        target_hours = self.strategy.calculate_target_hours(prices, self.strategy_data)

        if self.strategy_name == 'valley_detection':
            # For valley detection, store target hours in strategy data
            if not isinstance(self.strategy_data, ValleyDetectionStrategyData):
                logger.error(f"Invalid strategy data type for valley_detection [type={type(self.strategy_data)}]")
                return

            if target_hours:
                # Find the price for each target hour
                hour_prices = {h: p for h, p in prices}
                self.strategy_data.target_hours = target_hours
                self.strategy_data.target_prices = {h: hour_prices.get(h, 0) for h in target_hours}

                avg_price = self.strategy_data.get_average_price()
                logger.info(f"Valley detection calculated targets [plug_name={self.name}, hours={target_hours}, avg_price={avg_price:.4f}]")
            else:
                self.strategy_data.target_hours = []
                self.strategy_data.target_prices = {}

        else:
            # For period strategy, map target hours back to periods
            if not isinstance(self.strategy_data, PeriodStrategyData):
                logger.error(f"Invalid strategy data type for period [type={type(self.strategy_data)}]")
                return

            for period in self.strategy_data.periods:
                start_hour = period.start_hour
                end_hour = period.end_hour

                # Find cheapest hour in this period
                period_prices = [(h, p) for h, p in prices if start_hour <= h <= end_hour]
                if period_prices:
                    target_hour, target_price = min(period_prices, key=lambda x: x[1])
                    period.target_hour = target_hour
                    period.target_price = target_price
                else:
                    period.target_hour = None
                    period.target_price = None

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
            logger.error(f"Failed to get countdown rules [error={e}]")
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
            logger.info(f"Cancelled countdown rules [plug_name={self.name}]")
        except Exception as e:
            logger.error(f"Failed to cancel countdown rules [plug_name={self.name}, error={e}]")

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
            logger.error(f"Failed to get current power [error={e}]")
            return None


class PlugManager:
    """Manages shared plug instances that are used by both API and manager thread."""

    def __init__(self):
        self._plugs: list[Plug] = []
        self._lock = threading.Lock()

    def reload_plugs(self, automatic_only=False):
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
                automatic = is_plug_automatic(address)
                if (not automatic_only) or automatic:
                    new_plugs.append(Plug(config[section], tapo_email, tapo_password, automatic))

        with self._lock:
            self._plugs = new_plugs

        logger.info(f"Reloaded plugs from config [count={len(new_plugs)}]")

    def get_plugs(self, automatic_only=False) -> list[Plug]:
        """Get current plugs. Thread-safe read."""
        with self._lock:
            if automatic_only:
                return [p for p in self._plugs if p.automatic_schedules]
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
    """Load plug states from JSON file. True = automatic schedules enabled, False = manual mode."""
    try:
        with open(PLUG_STATES_FILE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_plug_states(states):
    """Save plug states to JSON file."""
    with open(PLUG_STATES_FILE_PATH, 'w') as f:
        json.dump(states, f, indent=2)


def is_plug_automatic(address: str) -> bool:
    """Check if plug is in automatic mode. True = automatic mode, False = manual mode."""
    states = _load_plug_states()
    return states.get(address, True)


def toggle_plug_automatic(address: str):
    """Toggle plug between automatic and manual mode. Preserves current plug state."""
    states = _load_plug_states()

    plug_exists = False
    for section in config.sections():
        if section.startswith("plug") and config[section].get('address') == address:
            plug_exists = True
            break

    if not plug_exists:
        raise ValueError("Plug not found")

    result = not states.get(address, True)
    states[address] = result
    _save_plug_states(states)

    plug = plug_manager.get_plug_by_address(address)
    if plug:
        with plug.acquire_lock():
            plug.automatic_schedules = result

    return result


def get_plugs(automatic_only=False) -> list[Plug]:
    """Get plugs from shared plug manager. If automatic_only=True, returns only plugs in automatic mode."""
    return plug_manager.get_plugs(automatic_only)


def get_plug_energy(address):
    p = plug_manager.get_plug_by_address(address)
    if not p:
        raise ValueError(f"Plug with address {address} not found")
    return p.get_hourly_energy()
