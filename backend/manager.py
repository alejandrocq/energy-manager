import configparser
import json
import os
import smtplib
import time
import requests
import logging
import re
import uuid
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from PyP100 import PyP100, auth_protocol, MeasureInterval
from providers import PROVIDERS, PricesProvider

CONFIG_FILE_PATH = "config/config.properties"
CHART_FILE_NAME = "prices_chart.png"
SCHEDULED_FILE_PATH = "data/schedules.json"
PLUG_STATES_FILE_PATH = "data/plug_states.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()

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


def human_time_to_seconds(human_time):
    match: re.Match = re.match(r"(\d+[h|m|s]?)(\d+[h|m|s]?)?(\d+[h|m|s]?)?", human_time)
    h = match.group(1)
    hours = int(h.replace('h', '') if h else 0)
    m = match.group(2)
    minutes = int(m.replace('m', '') if m else 0)
    s = match.group(3)
    seconds = int(s.replace('s', '') if s else 0)
    return hours * 3600 + minutes * 60 + seconds


def send_email(subject, content, from_email, to_email, attach_chart=False):
    mime_message = MIMEMultipart("related")
    mime_message["From"] = from_email
    mime_message["To"] = to_email
    mime_message["Subject"] = subject
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body>
    {content}
    {"<br><img src='cid:chart'>" if attach_chart else ""}
    </body>
    </html>
    """
    mime_text = MIMEText(html_body, "html", _charset="utf-8")
    mime_message.attach(mime_text)
    if attach_chart:
        with open(CHART_FILE_NAME, "rb") as f:
            chart = MIMEImage(f.read())
        chart.add_header("Content-ID", "<chart>")
        mime_message.attach(chart)
    try:
        with smtplib.SMTP('postfix') as smtp_server:
            smtp_server.sendmail(from_email, to_email, mime_message.as_string())
    except Exception as err:
        logging.error(f"Failed to send email: {err}")


def toggle_plug_enabled(address: str):
    # Load current states
    states = _load_plug_states()

    # Check if plug exists
    plug_exists = False
    for section in config.sections():
        if section.startswith("plug") and config[section].get('address') == address:
            plug_exists = True
            break

    if not plug_exists:
        raise ValueError("Plug not found")

    # Get current state (default to True if not found)
    current = states.get(address, True)

    # Turn plug off
    for plug in get_plugs():
        if plug.address == address:
            plug.tapo.turnOff()
            break

    # Save new state
    states[address] = not current
    _save_plug_states(states)


def get_plugs(enabled_only=False) -> list[Plug]:
    config.read(CONFIG_FILE_PATH)
    tapo_email = config.get('credentials', 'tapo_email')
    tapo_password = config.get('credentials', 'tapo_password')
    out = []
    for section in config.sections():
        if section.startswith("plug"):
            address = config[section].get('address')
            enabled = is_plug_enabled(address)
            if (not enabled_only) or enabled:
                out.append(Plug(config[section], tapo_email, tapo_password, enabled))
    return out


def get_provider():
    config.read(CONFIG_FILE_PATH)
    return PROVIDERS[config.get('settings', 'provider')]


def get_plug_energy(address):
    p: Plug = next(x for x in get_plugs() if x.address == address)
    return p.get_hourly_energy()


def _load_scheduled_events():
    """Load all scheduled events from JSON file."""
    try:
        with open(SCHEDULED_FILE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_scheduled_events(events):
    """Save scheduled events to JSON file."""
    with open(SCHEDULED_FILE_PATH, 'w') as f:
        json.dump(events, f, indent=2)


def create_scheduled_event(plug_address: str, plug_name: str, target_datetime: str, desired_state: bool, duration_seconds: int = None):
    """Create a new scheduled event for a plug."""
    events = _load_scheduled_events()

    # Normalize target_datetime to UTC
    target_dt = datetime.fromisoformat(target_datetime)
    if target_dt.tzinfo is None:
        # Assume UTC if no timezone info
        target_dt = target_dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        target_dt = target_dt.astimezone(timezone.utc)

    event = {
        'id': str(uuid.uuid4()),
        'plug_address': plug_address,
        'plug_name': plug_name,
        'target_datetime': target_dt.isoformat(),  # Always stored as UTC
        'desired_state': desired_state,  # True = ON, False = OFF
        'duration_seconds': duration_seconds,
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    events.append(event)
    _save_scheduled_events(events)
    logging.info(f"Created scheduled event: {event}")
    return event


def get_scheduled_events(plug_address: str = None):
    """Get all scheduled events, optionally filtered by plug address."""
    events = _load_scheduled_events()
    if plug_address:
        events = [e for e in events if e['plug_address'] == plug_address]
    return [e for e in events if e['status'] == 'pending']


def delete_scheduled_event(event_id: str):
    """Delete a scheduled event by ID."""
    events = _load_scheduled_events()
    for event in events:
        if event['id'] == event_id:
            event['status'] = 'cancelled'
            event['cancelled_at'] = datetime.now(timezone.utc).isoformat()
            logging.info(f"Cancelled scheduled event: {event}")
            _save_scheduled_events(events)
            return True
    return False


def process_scheduled_events(plugs: list[Plug], manager_from_email: str, manager_to_email: str):
    """Process pending scheduled events and execute if time has arrived."""
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)
    modified = False

    for event in events:
        if event['status'] != 'pending':
            continue

        target_dt = datetime.fromisoformat(event['target_datetime'])

        if target_dt <= now:
            # Time to execute
            plug_address = event['plug_address']
            plug_name = event.get('plug_name', 'Unknown')
            desired_state = event.get('desired_state', True)  # Default to ON for backward compatibility

            # Find the plug
            plug = next((p for p in plugs if p.address == plug_address), None)
            if plug:
                try:
                    # Cancel all countdown timers first to avoid Tapo API errors
                    plug.cancel_countdown_rules()

                    # Turn plug to desired state
                    if desired_state:
                        plug.tapo.turnOn()
                        state_str = "ON"
                    else:
                        plug.tapo.turnOff()
                        state_str = "OFF"

                    logging.info(f"Executed scheduled event for {plug_name} at {now}: turned {state_str}")

                    # If duration specified, set opposite state timer
                    duration_seconds = event.get('duration_seconds')
                    if duration_seconds and duration_seconds > 0:
                        if desired_state:
                            plug.tapo.turnOffWithDelay(duration_seconds)
                            logging.info(f"Plug {plug_name} will turn OFF in {timedelta(seconds=duration_seconds)}")
                        else:
                            plug.tapo.turnOnWithDelay(duration_seconds)
                            logging.info(f"Plug {plug_name} will turn ON in {timedelta(seconds=duration_seconds)}")

                    # Send email notification
                    email_message = f"🔌 Plug {plug_name} has been turned {state_str} per scheduled event at {now}."
                    if duration_seconds and duration_seconds > 0:
                        opposite_state = "OFF" if desired_state else "ON"
                        email_message += f"<br>It will turn {opposite_state} in {timedelta(seconds=duration_seconds)}."
                    send_email(
                        f"🔌 Plug {plug_name} scheduled {state_str} executed",
                        email_message,
                        manager_from_email,
                        manager_to_email
                    )

                    event['status'] = 'completed'
                    event['executed_at'] = now.isoformat()
                    modified = True

                except Exception as err:
                    logging.error(f"Error executing scheduled event for {plug_name}: {err}")
                    event['status'] = 'failed'
                    event['error'] = str(err)
                    event['failed_at'] = now.isoformat()
                    modified = True
            else:
                logging.error(f"Plug {plug_address} not found for scheduled event")
                event['status'] = 'failed'
                event['error'] = 'Plug not found'
                event['failed_at'] = now.isoformat()
                modified = True

    if modified:
        _save_scheduled_events(events)

    # Clean up old completed/cancelled events (older than 7 days)
    _cleanup_old_events()


def _cleanup_old_events():
    """Remove old completed/cancelled events from storage."""
    events = _load_scheduled_events()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    active_events = []
    for e in events:
        if e['status'] == 'pending':
            active_events.append(e)
            continue

        event_dt = datetime.fromisoformat(e.get('created_at') or e.get('cancelled_at') or e.get('executed_at') or now.isoformat())

        if event_dt > cutoff:
            active_events.append(e)

    if len(active_events) != len(events):
        _save_scheduled_events(active_events)
        logging.info(f"Cleaned up {len(events) - len(active_events)} old scheduled events")


def _load_plug_states():
    """Load plug enabled/disabled states from JSON file."""
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
    """Check if a plug is enabled based on its address."""
    states = _load_plug_states()
    # Default to True if not found (backward compatibility)
    return states.get(address, True)


if __name__ == '__main__':
    last_config_mtime = None
    last_states_mtime = None
    target_date = None

    manager_from_email = None
    manager_to_email = None
    provider: PricesProvider | None = None
    plugs = []

    while True:
        current_config_mtime = os.path.getmtime(CONFIG_FILE_PATH)

        # Check if plug_states.json exists and get its mtime
        try:
            current_states_mtime = os.path.getmtime(PLUG_STATES_FILE_PATH)
        except FileNotFoundError:
            current_states_mtime = None

        # Reload if config or plug states have changed
        config_changed = current_config_mtime != last_config_mtime
        states_changed = current_states_mtime != last_states_mtime

        if config_changed or states_changed:
            if config_changed:
                logging.info(f"{CONFIG_FILE_PATH} changed, recalculating prices...")
                last_config_mtime = current_config_mtime
                config.read(CONFIG_FILE_PATH)
                manager_from_email = config.get('email', 'from_email')
                manager_to_email = config.get('email', 'to_email')
                provider = get_provider()
                target_date = None  # Force reloading prices

            if states_changed:
                logging.info(f"{PLUG_STATES_FILE_PATH} changed, reloading plugs...")
                last_states_mtime = current_states_mtime

            # Always reload plugs when either file changes
            plugs = get_plugs(True)

        if (target_date is None or target_date.date() != datetime.now().date()) and not provider.unavailable():
            target_date = datetime.now()
            current_date = target_date.strftime("%Y%m%d")
            current_date_on_file = target_date.strftime("%Y;%m;%d")

            logging.info(f"Loading prices data for {target_date.date()}")

            hourly_prices = provider.get_prices(target_date)
            if not hourly_prices:
                logging.warning(f"No prices data available for {target_date.date()}. Skipping email.")
                continue

            email_message = f"<p>💶🔋 Electricity prices for {target_date.date()}:</p>"
            for hour, price in hourly_prices:
                email_message += f"⏱️💶 {hour}h: {price} €/kWh<br>"

            for plug in plugs:
                plug.calculate_target_hours(hourly_prices)

                email_message += "<p>"
                email_message += f"🔌 {plug.name}:<br>"
                for period in plug.periods:
                    if not period['target']:
                        continue

                    sh = period['start_hour']
                    eh = period['end_hour']
                    th, tp = period['target']
                    rt_h = period['runtime_human']
                    rt_s = period['runtime_seconds']
                    email_message += (
                        f"⬇️💶 Cheapest hour within period ({sh}h - {eh}h): "
                        f"{th}h - {tp} €/kWh<br>"
                    )
                    email_message += (
                        f"⏱️ Plug will run for {rt_h} "
                        f"({rt_s} seconds) in this period.<br>"
                    )
                email_message += "</p>"

            try:
                os.remove(CHART_FILE_NAME)
            except OSError:
                pass

            fig, ax = plt.subplots()
            ax.bar([h for h, p in hourly_prices], [p for h, p in hourly_prices])
            ax.set_title(f"Electricity prices for {target_date.date()}")
            ax.set_xlabel("Hour")
            ax.set_ylabel("Price (€/kWh)")
            fig.savefig(CHART_FILE_NAME)

            send_email(
                f'💶🔋 Electricity prices for {target_date.date()}',
                email_message,
                manager_from_email,
                manager_to_email,
                True
            )
            logging.info(f"Successfully downloaded prices data for {target_date.date()} and sent email.")
        else:
            for plug in plugs:
                try:
                    runtime = plug.runtime_seconds()
                    if runtime > 0:
                        if not plug.tapo.get_status():
                            plug.tapo.turnOn()
                            plug.tapo.turnOffWithDelay(runtime)
                            logging.info(
                                f"Plug {plug.name} enabled at {datetime.now()} for {timedelta(seconds=runtime)}"
                            )
                            send_email(
                                f"🔌 Plug {plug.name} enabled",
                                f"🔌 Plug {plug.name} has been enabled for {timedelta(seconds=runtime)}.",
                                manager_from_email,
                                manager_to_email
                            )
                    else:
                        if plug.tapo.get_status() and plug.get_rule_remain_seconds() is None:
                            default_runtime = plug.periods[0]['runtime_seconds'] if plug.periods else 0
                            if default_runtime == 0:
                                continue

                            plug.tapo.turnOffWithDelay(default_runtime)
                            logging.info(
                                f"Plug {plug.name} is on outside cheapest hours, "
                                f"scheduled turn-off in {timedelta(seconds=default_runtime)}"
                            )
                            send_email(
                                f"🔌 Plug {plug.name} scheduled turn off",
                                f"Plug {plug.name} was on outside cheapest hours and will be turned off in "
                                f"{timedelta(seconds=default_runtime)}.",
                                manager_from_email,
                                manager_to_email
                            )
                except Exception as err:
                    logging.error(f"Error while processing plug {plug.name}: {err}")
                    if isinstance(plug.tapo.protocol, auth_protocol.AuthProtocol):
                        try:
                            plug.tapo.protocol.session = requests.Session()
                            plug.tapo.protocol.Initialize()
                            logging.info("Successfully re-initialized plug protocol")
                        except Exception as err:
                            logging.error(f"Failed to re-initialize plug protocol: {err}")

        # Process scheduled events
        if manager_from_email and manager_to_email:
            process_scheduled_events(plugs, manager_from_email, manager_to_email)

        try:
            time.sleep(30)
        except KeyboardInterrupt:
            logging.info("Exiting…")
            break
