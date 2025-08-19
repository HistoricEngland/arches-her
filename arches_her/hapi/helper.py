import re
import logging
from django.core.mail import EmailMessage
from arches.app.models.system_settings import settings


def parse_date(date: str) -> str:
    """
    Removes Y and ? from date strings.
    
    Although valid ETDF dates can contain 'Y' and '?', these characters are not valid for H.API.
    """
    return re.sub(r'\?|y', '', date, flags=re.IGNORECASE) if date else None

def send_email(subject: str, body: str, to: str) -> None:
    email = EmailMessage(subject, body, to=[to], from_email=settings.DEFAULT_FROM_EMAIL)

    try:
        email.send()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send email: {e}")


def email_error(body: str, error: str, to: str = settings.HAPI_ERROR_EMAIL, subject: str = "H.API Error") -> None:
    send_email(subject, f"{body}\n\n{error}", to)
