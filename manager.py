import configparser
import smtplib
import time
import requests
import logging
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from PyP100 import PyP100, auth_protocol

FIRST_PERIOD_OFF_DELAY = timedelta(hours=2).total_seconds()
SECOND_PERIOD_OFF_DELAY = timedelta(hours=1).total_seconds()
CHART_FILE_NAME = "electricity_prices_chart.png"

SMTP_SERVER = smtplib.SMTP('localhost')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def send_email(subject, content, from_email, to_email, attach_chart=False):
    mime_message = MIMEMultipart("related")
    mime_message["From"] = f"Energy manager <{from_email}>"
    mime_message["To"] = f"Alejandro Castilla Quesada <{to_email}>"
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

    SMTP_SERVER.sendmail(from_email, to_email, mime_message.as_string())


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.properties')
    manager_from_email = config.get('email', 'manager.from.email')
    manager_to_email = config.get('email', 'manager.to.email')
    tapo_address = config.get('credentials', 'tapo.address')
    tapo_email = config.get('credentials', 'tapo.email')
    tapo_password = config.get('credentials', 'tapo.password')

    plug = PyP100.Switchable(tapo_address, tapo_email, tapo_password, "old")

    target_date = None
    target_hour_first_period = None
    target_hour_second_period = None

    while True:
        if (target_date is None or target_date.date() != datetime.now().date()) or target_hour_first_period is None:
            target_date = datetime.now()
            target_hour_first_period = None
            target_hour_second_period = None

            logging.info(f"Loading prices data for {target_date.date()}")

            current_date = target_date.strftime("%Y%m%d")
            current_date_on_file = target_date.strftime("%Y;%m;%d")
            current_hour = target_date.hour

            url = f"https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_{current_date}.1"
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
                            price = float(parts[5])
                            hourly_prices.append((hour, price))

                    target_hour_first_period = min(
                        [(hour, price) for hour, price in hourly_prices if 3 <= hour <= 10],
                        key=lambda x: x[1])
                    target_hour_second_period = min(
                        [(hour, price) for hour, price in hourly_prices if 14 <= hour <= 23],
                        key=lambda x: x[1])

                    email_message = f"<p>💶🔋 Electricity prices for {datetime.now().date()}:</p>"

                    for hour, price in hourly_prices:
                        email_message += f"⏱️💶 {hour}h: {price} €/MWh"
                        email_message += "<br>"

                    email_message += "<p>"

                    cheapest_hour_message_first_period = (
                        f"⬇️💶 Cheapest hour within first period: {target_hour_first_period[0]}h - "
                        f"{target_hour_first_period[1]} €/MWh")
                    cheapest_hour_message_second_period = (
                        f"⬇️💶 Cheapest hour within second period: {target_hour_second_period[0]}h - "
                        f"{target_hour_second_period[1]} €/MWh")


                    email_message += cheapest_hour_message_first_period
                    email_message += "<br>"
                    email_message += cheapest_hour_message_second_period

                    email_message += "</p>"

                    plt.bar([hour for hour, price in hourly_prices], [price for hour, price in hourly_prices])
                    plt.xlabel("Hour")
                    plt.ylabel("Price (€/MWh)")
                    plt.title("Electricity prices")
                    plt.savefig(CHART_FILE_NAME)

                    send_email(f'Electricity prices for {target_date.date()}', email_message,
                               manager_from_email, manager_to_email, True)

                    logging.info(f"Successfully downloaded prices data for {target_date.date()}. "
                                 f"Email with all data has been sent.")
                except Exception as e:
                    logging.error(f"Failed to parse prices data: {e}")
            else:
                logging.error(f"Failed to download prices data. Response code: {response.status_code}")
        else:
            # Check if we are in some of the cheapest hours and enable the plug
            is_first_target = target_hour_first_period[0] == datetime.now().hour
            is_second_target = target_hour_second_period[0] == datetime.now().hour
            if is_first_target or is_second_target:
                try:
                    if not plug.get_status():
                        delay = FIRST_PERIOD_OFF_DELAY if is_first_target else SECOND_PERIOD_OFF_DELAY
                        plug.turnOn()
                        plug.turnOffWithDelay(delay)
                        logging.info(f"Plug enabled at {datetime.now()} for {timedelta(seconds=delay)}")
                        send_email("Plug enabled",
                                   f"🔌 Plug has been enabled for {timedelta(seconds=delay)}.",
                                   manager_from_email, manager_to_email)
                except Exception as e:
                    logging.error(f"Failed to enable plug: {e}")
                    # Try to re-initialize the protocol
                    if isinstance(plug.protocol, auth_protocol.OldProtocol):
                        # WARNING: session must be re-initialized because the plug does not seem to allow more than
                        # one handshake in the same session.
                        # See https://github.com/fishbigger/TapoP100/issues/62#issuecomment-1107876214
                        try:
                            plug.protocol.session = requests.Session()
                            plug.protocol.Initialize()
                        except Exception as e:
                            logging.error(f"Failed to re-initialize plug protocol: {e}")

                        logging.info("Successfully re-initialized plug protocol")

        time.sleep(30)
