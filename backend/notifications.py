from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("uvicorn.error")


def send_email(subject, content, from_email, to_email, attach_chart=False):
    """Send HTML email via postfix SMTP server.

    Args:
        subject: Email subject line
        content: HTML content (should be complete HTML document)
        from_email: Sender email address
        to_email: Recipient email address
        attach_chart: Deprecated parameter, kept for backwards compatibility
    """
    mime_message = MIMEMultipart("related")
    mime_message["From"] = from_email
    mime_message["To"] = to_email
    mime_message["Subject"] = subject

    # Content should already be a complete HTML document from email_templates
    mime_text = MIMEText(content, "html", _charset="utf-8")
    mime_message.attach(mime_text)

    try:
        with smtplib.SMTP('postfix') as smtp_server:
            smtp_server.sendmail(from_email, to_email, mime_message.as_string())
    except Exception as err:
        logger.error(f"Failed to send email [error={err}]")
