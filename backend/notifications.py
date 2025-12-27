from __future__ import annotations

import logging
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import CHART_FILE_NAME

logger = logging.getLogger("uvicorn.error")


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
        logger.error(f"Failed to send email [error={err}]")
