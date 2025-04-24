import configparser
import os
import smtplib
import time
import requests
import logging
import re
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from PyP100 import PyP100, auth_protocol, MeasureInterval
from providers import PROVIDERS

CHART_FILE_NAME = "prices_chart.png"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
config.read('config.properties')

manager_from_email = config.get('email', 'from_email')
manager_to_email = config.get('email', 'to_email')

tapo_email = config.get('credentials', 'tapo_email')
tapo_password = config.get('credentials', 'tapo_password')

provider_key = config.get('settings', 'provider')
provider = PROVIDERS[provider_key]()


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
        with smtplib.SMTP('localhost') as smtp_server:
            smtp_server.sendmail(from_email, to_email, mime_message.as_string())
    except Exception as err:
        logging.error(f"Failed to send email: {err}")


def get_plugs():
    config = configparser.ConfigParser()
    config.read('config.properties')
    plugs = []
    for section in config.sections():
        if section.startswith("plug") and config[section].getboolean('enabled'):
            plugs.append(Plug(config[section], tapo_email, tapo_password))
    return plugs


def get_plug_energy(address):
    p = next(x for x in get_plugs() if x.address == address)
    return p.get_hourly_energy()


class Plug:
    def __init__(self, plug_config: configparser.SectionProxy, email: str, password: str):
        self.name = plug_config.get('name')
        self.address = plug_config.get('address')
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


if __name__ == '__main__':
    target_date = None

    while True:
        if target_date is None or target_date.date() != datetime.now().date():
            target_date = datetime.now()
            current_date = target_date.strftime("%Y%m%d")
            current_date_on_file = target_date.strftime("%Y;%m;%d")

            logging.info(f"Loading prices data for {target_date.date()}")

            hourly_prices = provider.get_prices(target_date)

            email_message = f"<p>💶🔋 Electricity prices for {target_date.date()}:</p>"
            for hour, price in hourly_prices:
                email_message += f"⏱️💶 {hour}h: {price} €/kWh<br>"

            for plug in get_plugs():
                plug.calculate_target_hours(hourly_prices)

                email_message += "<p>"
                email_message += f"🔌 {plug.name}:<br>"
                for period in plug.periods:
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
            for plug in get_plugs():
                runtime = plug.runtime_seconds()
                if runtime > 0:
                    try:
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
                    except Exception as e:
                        logging.error(f"Failed to enable plug: {e}")
                        if isinstance(plug.tapo.protocol, auth_protocol.AuthProtocol):
                            try:
                                plug.tapo.protocol.session = requests.Session()
                                plug.tapo.protocol.Initialize()
                                logging.info("Successfully re-initialized plug protocol")
                            except Exception as err:
                                logging.error(f"Failed to re-initialize plug protocol: {err}")
                else:
                    try:
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
                    except Exception as e:
                        logging.error(f"Failed to set default runtime for plug: {e}")

        try:
            time.sleep(30)
        except KeyboardInterrupt:
            logging.info("Exiting…")
            break
