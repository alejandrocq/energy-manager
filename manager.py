import configparser
import os
import smtplib
import time

import matplotlib.axes
import requests
import logging
import re
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from PyP100 import PyP100, auth_protocol

CHART_FILE_NAME = "prices_chart.png"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Plug:
    def __init__(self, plug_config: configparser.SectionProxy, email: str, password: str):
        self.name = plug_config.get('name')
        self.address = plug_config.get('address')
        self.first_period_start_hour = plug_config.getint('first_period_start_hour')
        self.first_period_end_hour = plug_config.getint('first_period_end_hour')
        self.first_period_runtime_human = plug_config.get('first_period_runtime_human')
        self.first_period_runtime_seconds = human_time_to_seconds(self.first_period_runtime_human)
        self.second_period_start_hour = plug_config.getint('second_period_start_hour')
        self.second_period_end_hour = plug_config.getint('second_period_end_hour')
        self.second_period_runtime_human = plug_config.get('second_period_runtime_human')
        self.second_period_runtime_seconds = human_time_to_seconds(self.second_period_runtime_human)
        self.tapo = PyP100.Switchable(self.address, email, password)

        self.first_period_target = None
        self.second_period_target = None

    def calculate_target_hours(self, prices: list[tuple[int, float]]):
        self.first_period_target = min([(h, p) for h, p in prices
                                        if self.first_period_start_hour <= h <= self.first_period_end_hour],
                                       key=lambda x: x[1])
        self.second_period_target = min([(h, p) for h, p in prices
                                         if self.second_period_start_hour <= h <= self.second_period_end_hour],
                                        key=lambda x: x[1])

    def runtime_seconds(self):
        current_hour = datetime.now().hour
        if self.first_period_target[0] == current_hour:
            return self.first_period_runtime_seconds
        elif self.second_period_target[0] == current_hour:
            return self.second_period_runtime_seconds
        else:
            return 0


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


def human_time_to_seconds(human_time):
    match: re.Match = re.match(r"(\d+[h|m|s]?)(\d+[h|m|s]?)?(\d+[h|m|s]?)?", human_time)
    h = match.group(1)
    hours = int(h.replace('h', '') if h else 0)
    m = match.group(2)
    minutes = int(m.replace('m', '') if m else 0)
    s = match.group(3)
    seconds = int(s.replace('s', '') if s else 0)

    # Convert the hours, minutes, and seconds to seconds.
    total_seconds = hours * 3600 + minutes * 60 + seconds

    return total_seconds


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.properties')

    manager_from_email = config.get('email', 'from_email')
    manager_to_email = config.get('email', 'to_email')
    tapo_email = config.get('credentials', 'tapo_email')
    tapo_password = config.get('credentials', 'tapo_password')

    plugs = []
    for section in config.sections():
        if section.startswith("plug"):
            if config[section].getboolean('enabled'):
                plugs.append(Plug(config[section], tapo_email, tapo_password))

    target_date = None

    while True:
        if target_date is None or target_date.date() != datetime.now().date():
            target_date = datetime.now()
            current_date = target_date.strftime("%Y%m%d")
            current_date_on_file = target_date.strftime("%Y;%m;%d")

            logging.info(f"Loading prices data for {target_date.date()}")

            url = (f"https://www.omie.es/es/file-download?parents=marginalpdbc"
                   f"&filename=marginalpdbc_{current_date}.1")
            response = requests.get(url)
            if response.status_code == 200:
                try:
                    file_content = response.text
                    hourly_prices = []
                    for line in file_content.split("\n"):
                        if line and line.startswith(current_date_on_file):
                            parts = line.split(";")
                            # IMPORTANT: OMIE provides every price at the end of the hour, so we need to subtract 1 hour
                            # This can be checked in the charts of esios.ree.es
                            hour = int(parts[3]) - 1
                            price = round(float(parts[5]) / 1000, 3)
                            hourly_prices.append((hour, price))

                    email_message = f"<p>💶🔋 Electricity prices for {datetime.now().date()}:</p>"

                    for hour, price in hourly_prices:
                        email_message += f"⏱️💶 {hour}h: {price} €/kWh"
                        email_message += "<br>"

                    for plug in plugs:
                        plug.calculate_target_hours(hourly_prices)
                        email_message += "<p>"
                        email_message += f"🔌 {plug.name}:"
                        email_message += "<br>"
                        email_message += f"⬇️💶 Cheapest hour within first period " \
                                         f"({plug.first_period_start_hour}h - {plug.first_period_end_hour}h): " \
                                         f"{plug.first_period_target[0]}h - {plug.first_period_target[1]} €/kWh"
                        email_message += "<br>"
                        email_message += (f"⏱️ Plug will run for {plug.first_period_runtime_human} "
                                          f"({plug.first_period_runtime_seconds} seconds) in this period.")
                        email_message += "<br>"
                        email_message += f"⬇️💶 Cheapest hour within second period " \
                                         f"({plug.second_period_start_hour}h - {plug.second_period_end_hour}h): " \
                                         f"{plug.second_period_target[0]}h - {plug.second_period_target[1]} €/kWh"
                        email_message += "<br>"
                        email_message += (f"⏱️ Plug will run for {plug.second_period_runtime_human} "
                                          f"({plug.second_period_runtime_seconds} seconds) in this period.")
                        email_message += "</p>"

                    # Delete previous chart
                    try:
                        os.remove(CHART_FILE_NAME)
                    except OSError:
                        pass

                    ax: matplotlib.axes.Axes
                    fig: matplotlib.pyplot.Figure
                    (fig, ax) = plt.subplots()
                    ax.bar([hour for hour, price in hourly_prices], [price for hour, price in hourly_prices])
                    ax.set_title(f"Electricity prices for {target_date.date()}")
                    ax.set_xlabel("Hour")
                    ax.set_ylabel("Price (€/kWh)")
                    fig.savefig(CHART_FILE_NAME)

                    send_email(f'💶🔋 Electricity prices for {target_date.date()}', email_message,
                               manager_from_email, manager_to_email, True)

                    logging.info(f"Successfully downloaded prices data for {target_date.date()}. "
                                 f"Email with all data has been sent.")
                except Exception as e:
                    logging.error(f"Failed to parse prices data: {e}", e)
            else:
                logging.error(f"Failed to download prices data. Response code: {response.status_code}")
        else:
            # Check if we are in some of the cheapest hours and enable the plug
            for plug in plugs:
                runtime = plug.runtime_seconds()
                if runtime > 0:  # We are on target
                    try:
                        if not plug.tapo.get_status():
                            plug.tapo.turnOn()
                            plug.tapo.turnOffWithDelay(runtime)
                            logging.info(
                                f"Plug {plug.name} enabled at {datetime.now()} for {timedelta(seconds=runtime)}")
                            send_email(f"🔌 Plug {plug.name} enabled",
                                       f"🔌 Plug {plug.name} has been enabled for {timedelta(seconds=runtime)}.",
                                       manager_from_email, manager_to_email)
                    except Exception as e:
                        logging.error(f"Failed to enable plug: {e}")
                        # Try to re-initialize the protocol
                        if isinstance(plug.tapo.protocol, auth_protocol.AuthProtocol):
                            # WARNING: session must be re-initialized because the plug does not seem to allow more than
                            # one handshake in the same session.
                            # See https://github.com/fishbigger/TapoP100/issues/62#issuecomment-1107876214
                            try:
                                plug.tapo.protocol.session = requests.Session()
                                plug.tapo.protocol.Initialize()
                            except Exception as e:
                                logging.error(f"Failed to re-initialize plug protocol: {e}")

                            logging.info("Successfully re-initialized plug protocol")

        try:
            time.sleep(30)
        except KeyboardInterrupt:
            logging.info("Exiting...")
            break
