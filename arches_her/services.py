import os
import uuid
import requests
import json
import logging
from arches.app.models.system_settings import settings
from typing import Dict, List, Optional, Union
from .data_access.common import (
    call_hapi_get_resources,
    call_hapi_get_descriptions,
    call_hapi_get_point_geometry,
    call_hapi_get_complex_geometry,
    call_hapi_get_object_finds,
    call_hapi_get_maritime_craft,
    call_hapi_get_historic_aircraft,
    call_hapi_get_related_monument_records,
    call_hapi_get_related_events,
    get_images,
    get_other_statuses,
    generate_json,
    get_protected_statuses
)
from .data_access.monument import (
    call_get_monument_dated_types,
    get_monument_sources
)
from .models.factory import create_resource


logger = logging.getLogger(__name__)

def is_valid_uuid(uuid_to_test: str) -> bool:
    """Check if the provided UUID is valid."""
    try:
        uuid_obj = uuid.UUID(uuid_to_test)
    except ValueError as e:
        return False
    return str(uuid_obj) == uuid_to_test


def validate_uuids(uuid_input: str) -> List[str]:
    if os.path.isfile(uuid_input):
        with open(uuid_input, 'r') as file:
            uuid_list = [line.strip() for line in file.readlines()
                         if not line.strip().startswith(('#', '--'))]
    else:
        uuid_list = [uuid.strip() for uuid in uuid_input.split(',')]

    for u in uuid_list:
        if not is_valid_uuid(u):
            raise ValueError(f"Invalid UUID: {u}")
    return uuid_list

def validate_filename(filename: str):
    """Validate if the provided filename or path is valid."""
    if not os.path.isfile(filename) and not os.path.isdir(os.path.dirname(filename)):
        raise ValueError(f"Invalid filename or path: {filename}")


def validate(resource_uuid=None, input: str = None, output: str = None) -> Union[dict, bool]:

    url = settings.HAPI_VALIDATE_URL

    data = generate(resource_uuid, input)

    try:
        response = requests.post(url, json=data)
        if response.status_code not in [200, 422]:
            response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}")    
    
    if response.status_code == 200: # No errors
        returnVal = (True, response.status_code)
    elif response.status_code == 422: # Validation errors present
        returnVal =  ({"response": response.json(), "data": data}, response.status_code)
    else:
        returnVal =  ({"reason": response.reason}, response.status_code)

    if output:
        validate_filename(output)
        with open(output, 'w') as file:
            file.write(json.dumps(returnVal[0], indent=4))
        return None
    else:
        return returnVal

def generate(resource_uuid=None, input: str = None, output: str = None, batch_id: str = None) -> Optional[str]:
    if resource_uuid:
        uuid_list = validate_uuids(resource_uuid)
    else:
        validate_filename(input)
        uuid_list = validate_uuids(input)

    data = generate_data(uuid_list, batch_id=batch_id)

    if output:
        validate_filename(output)
        with open(output, 'w') as file:
            file.write(data)
        return None
    else:
        return data

def generate_data(uuid_list: List[uuid.UUID], batch_id: str = None) -> str:
    results = call_hapi_get_resources(resource_instance_ids=uuid_list)
    records = []
    for result in results:
        resource = create_resource(
            resource_type=result["resource_type"],
            resource_instance_id=result["resource_instance_id"],
            primary_reference_number=result["primary_reference_number"],
            heritage_asset_name=result["resource_name"],
            descriptions=call_hapi_get_descriptions(
                result["resource_instance_id"]),
            monument_dated_types=call_get_monument_dated_types(
                result["resource_instance_id"]),
            point_geometry=call_hapi_get_point_geometry(
                result["resource_instance_id"]),
            complex_geometry=call_hapi_get_complex_geometry(
                result["resource_instance_id"]),
            monument_sources=get_monument_sources(
                result["resource_instance_id"]),
            object_finds=call_hapi_get_object_finds(
                result["resource_instance_id"]),
            maritime_craft=call_hapi_get_maritime_craft(
                result["resource_instance_id"]),
            historic_aircraft=call_hapi_get_historic_aircraft(
                result["resource_instance_id"]),
            related_monument_records=call_hapi_get_related_monument_records(
                result["resource_instance_id"]),
            related_events=call_hapi_get_related_events(
                result["resource_instance_id"]),
            images=get_images(result["resource_instance_id"]),
            other_statuses=get_other_statuses(
                result["resource_instance_id"]),
            protected_statuses=get_protected_statuses(
                result["resource_instance_id"]),
            last_updated=result["most_recent_timestamp"]
        )
        records.append({"record": resource.__dict__})

    data = {"records": records}
    if batch_id:
        data = {"batch_id": batch_id, **data}

    json = generate_json(data)
    return json

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