from arches.app.models.system_settings import settings
from typing import Dict, Optional, Union
import requests
from django.core.management import call_command
import json
from io import StringIO
import logging

logger = logging.getLogger(__name__)

def validate(resource_uuid) -> Union[dict, bool]:
    output = StringIO()
    call_command("hapi", "generate", resource_uuid=resource_uuid, internal_call="True", stdout=output)
    resource_data = output.getvalue()

    url = settings.HAPI_VALIDATE_URL
    resource_data = resource_data.replace('\n', '').replace('\r', '').strip()
    resource_data = json.loads(resource_data)
    
    try:
        response = requests.post(url, json=resource_data)
        if response.status_code not in [200, 422]:
            response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}")    
    
    if response.status_code == 200: # No errors
        return True, response.status_code
    elif response.status_code == 422: # Validation errors present
        return {"response": response.json(), "data": resource_data}, response.status_code
    else:
        return {"reason": response.reason}, response.status_code

def generate(resource_uuid) -> dict:
    output = StringIO()
    call_command("hapi", "generate", resource_uuid=resource_uuid, internal_call="True", stdout=output)
    resource_data = output.getvalue()
    resource_data = resource_data.replace('\n', '').replace('\r', '').strip()
    resource_data = json.loads(resource_data)
    return {"data": resource_data}

def authenticate(username: str, password: str) -> Optional[str]:
    url = settings.HAPI_AUTHENTICATE_URL
    try:
        response = requests.post(url, json={"username": username, "password": password})
        if response.status_code != 200:
            response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}")
    
    token = None
    if response.status_code == 200:
        token = response.json()["token"]
    return token

def batch_create(counts: Dict, bearer_token: str = None, username: str = None, password: str = None) -> Optional[int]:
    url = settings.HAPI_BATCH_CREATE_URL
    if not bearer_token:
        bearer_token = authenticate(username, password)
    if not bearer_token:
        return None
    try:
        # TODO Need to send the bearer token in the Authorization
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.post(url, json=counts, headers=headers)
        response.raise_for_status()
        return response.json()["batch_id"]
    except requests.RequestException as e:
        logger.error(f"H.API batch creation failed: {e}")
        return None

def batch_submit(self, batch_id: str) -> bool:
    url = settings.HAPI_BATCH_SUBMIT_URL
    response = requests.post(url)
    return response.status_code == 200