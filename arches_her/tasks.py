import datetime
from celery import shared_task
from django.core.management import call_command
import logging
from io import StringIO

@shared_task
def add(x, y):
    z = x + y
    return z


@shared_task
def hapi_upload(interval: str, *args, **kwargs):
    logger = logging.getLogger(__name__)
    result = None
    # TODO: Get the timestamp of the last time the HAPI was run
    # TODO: Call the management command equivalent of manage.py hapi pending --interval passing in the interval value as an argument
    try:
        output = StringIO()
        call_command("hapi", "upload", interval=interval, internal_call="True", stdout=output)
        result = output.getvalue().replace('\n', '').replace('\r', '').strip()
    except Exception as e:
        logger.error(f"Error running H.API upload: {e}")
        return e
    return result
