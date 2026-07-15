import os
import uuid
import requests
import json
import logging
import functools
import time
from arches.app.models.system_settings import settings
from typing import Dict, List, Optional, Union
from typing import Callable, Any, TypeVar, cast
from arches.app.models.system_settings import settings
from arches_her.models.complex_geometry import ComplexGeometry
from arches_her.models.descriptions import Description
from arches_her.models.historic_aircraft_data import HistoricAircraftData
from arches_her.models.images import Image
from arches_her.models.maritime_craft import MaritimeCraft
from arches_her.models.monument_dated_types import MonumentDatedTypes
from arches_her.models.monument_sources import MonumentSource
from arches_her.models.object_finds import ObjectFinds
from arches_her.models.point_geometry import PointGeometry
from arches_her.models.related_events import RelatedEvent
from arches_her.models.related_monument_records import RelatedMonumentRecord

from .data_access.common import (
    get_resources,
    get_descriptions,
    get_point_geometry,
    get_complex_geometry,
    get_object_finds,
    get_maritime_craft,
    get_historic_aircraft,
    get_related_monument_records,
    get_related_events,
    get_images,
    get_other_statuses,
    generate_json,
    get_protected_statuses,
    get_monument_dated_types,
    get_monument_sources,
    get_processed_monument_sources,
)
from .models.factory import create_resource


logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry(max_attempts: int = 3, retry_delay_seconds: float = 1.0):
    """
    Decorator that retries a function execution if it raises an exception.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 1.0)

    Returns:
        The decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempts = 0
            last_exception = None

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    last_exception = e

                    if attempts < max_attempts:
                        logger.warning(
                            f"Attempt {attempts}/{max_attempts} for {func.__name__} failed: {str(e)}. "
                            f"Retrying in {retry_delay_seconds} seconds..."
                        )
                        time.sleep(retry_delay_seconds)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts for {func.__name__} failed. "
                            f"Last error: {str(e)}"
                        )

            # If we get here, all attempts failed
            if last_exception:
                raise last_exception

            # This should never happen, but makes the type checker happy
            raise RuntimeError("Unexpected state in retry decorator")

        return wrapper
    return decorator


def is_valid_uuid(uuid_to_test: str) -> bool:
    """Check if the provided UUID is valid."""
    try:
        uuid_obj = uuid.UUID(uuid_to_test)
    except ValueError as e:
        return False
    return str(uuid_obj) == uuid_to_test


def validate_uuids(uuid_input: str) -> List[str]:

    uuid_list = [uuid.strip() for uuid in uuid_input.split(',')]

    for u in uuid_list:
        if not is_valid_uuid(u):
            raise ValueError(f"Invalid UUID: {u}")
    return uuid_list


def get_heritage_asset_name(resource: Dict) -> str:
    """Extract the heritage asset name from a resource dictionary.

    Args:
        resource (Dict): The resource dictionary containing resource information

    Returns:
        str: The heritage asset name or a fallback using resource_type and primary_reference_number
              when resource_name is None
    """
    if resource["resource_name"] is not None:
        return resource["resource_name"]

    # Singularize the resource_type (simple rule: remove trailing 's' if present)
    resource_type = resource["resource_type"]
    if resource_type.endswith('s'):
        resource_type = resource_type[:-1]

    return f"{resource_type} {resource['primary_reference_number']}"


def get_primary_reference_number(resource: Dict) -> str:
    """Extract the primary reference number from a resource dictionary.

    This function retrieves the value associated with the key 
    'primary_reference_number' from the provided resource dictionary. 
    If the key exists and has a value, it returns that value; otherwise, 
    it returns None.

        resource (Dict): A dictionary containing resource information.

        str: The primary reference number if it exists, otherwise None.
    """
    return resource.get("primary_reference_number") or None


def validate(resource_uuid=None, resource_object=None) -> Union[dict, bool]:

    url = settings.HAPI_VALIDATE_URL

    data = generate(resource_uuid=resource_uuid,
                    resource_object=resource_object)

    response = requests.post(url, json=data)

    if response.status_code not in [200, 422]:
        response.raise_for_status()

    if response.status_code in [200, 422]:
        returnVal = ({"response": response.json(), "data": data},
                     response.status_code)
    else:
        returnVal = ({"response": {"reason": response.reason},
                     "data": data}, response.status_code)

    return returnVal


def generate(resource_uuid=None, resource_object=None, batch_id: str = None) -> Optional[str]:
    if resource_uuid:
        uuid_list = validate_uuids(resource_uuid)
    elif resource_object:
        uuid_list = None

    data = generate_data(uuid_list=uuid_list,
                         resource_object=resource_object, batch_id=batch_id)
    return data


def generate_data(uuid_list: List[uuid.UUID] = None, resource_object=None, batch_id: str = None) -> str:
    if resource_object:
        resources = resource_object
    else:
        resources = get_resources(resource_instance_ids=uuid_list)

    records = []

    excluded_fields_csv = getattr(settings, "HAPI_EXCLUDED_FIELDS", "") or ""

    if excluded_fields_csv and resources:
        CLASS_MAP = {
            "descriptions": Description,
            "monumentDatedTypes": MonumentDatedTypes,
            "pointGeometry": PointGeometry,
            "complexGeometries": ComplexGeometry,
            "monumentSources": MonumentSource,
            "objectFinds": ObjectFinds,
            "maritimeCraft": MaritimeCraft,
            "historicAircraft": HistoricAircraftData,
            "relatedMonumentRecords": RelatedMonumentRecord,
            "relatedEvents": RelatedEvent,
            "images": Image,
        }

        excluded_fields = set(f.strip()
                              for f in excluded_fields_csv.split(",") if f.strip())
        for field in excluded_fields:
            if "." not in field:
                logger.warning(
                    f"Invalid field format: {field}. Expected format is 'ClassName.field_name'. Skipping.")
                continue
            class_name, field_name = field.split(".")
            class_obj = CLASS_MAP.get(class_name, None)
            if class_obj is None:
                logger.warning(
                    f"Class {class_name} not found in CLASS_MAP. Skipping field {field_name}.")
                continue
            if hasattr(class_obj, 'excluded_fields'):
                class_obj.excluded_fields.add(field_name)
            else:
                logger.warning(
                    f"Class {class_name} does not have an 'excluded_fields' attribute. Skipping field {field_name}.")

    for resource in resources:
        if resource["deleted"]:
            resource = create_resource(
                resource_instance_id=resource["resource_instance_id"],
                primary_reference_number=get_primary_reference_number(
                    resource),
                delete=True
            )
        else:
            resource = create_resource(
                resource_instance_id=resource["resource_instance_id"],
                primary_reference_number=get_primary_reference_number(
                    resource),
                heritage_asset_name=get_heritage_asset_name(resource),
                descriptions=get_descriptions(
                    resource["resource_instance_id"]),
                monument_dated_types=get_monument_dated_types(
                    resource["resource_instance_id"]),
                point_geometry=get_point_geometry(
                    resource["resource_instance_id"]),
                complex_geometry=get_complex_geometry(
                    resource["resource_instance_id"]),
                monument_sources=get_processed_monument_sources(
                    resource["resource_instance_id"]),
                object_finds=get_object_finds(
                    resource["resource_instance_id"]),
                maritime_craft=get_maritime_craft(
                    resource["resource_instance_id"]),
                historic_aircraft=get_historic_aircraft(
                    resource["resource_instance_id"]),
                related_monument_records=get_related_monument_records(
                    resource["resource_instance_id"]),
                related_events=get_related_events(
                    resource["resource_instance_id"]),
                images=get_images(resource["resource_instance_id"]),
                protected_statuses=get_protected_statuses(
                    resource["resource_instance_id"]),
                other_statuses=get_other_statuses(
                    resource["resource_instance_id"]),
                last_updated=resource["most_recent_timestamp"],
                delete=resource["deleted"]
            )
        records.append({"record": resource.__dict__})

    data = {"records": records}
    if batch_id:
        data = {"batch_id": batch_id, **data}

    json = generate_json(data)
    return json


@retry(max_attempts=3, retry_delay_seconds=5)
def authenticate(username: str, password: str) -> Optional[str]:
    if not username or not password:
        logger.error("Username or password not provided for authentication.")
        return None

    url = settings.HAPI_AUTHENTICATE_URL
    payload = {"username": username, "password": password}

    response = requests.post(url, json=payload)
    response.raise_for_status()
    token = response.json().get("token")
    if token:
        logger.info("Authentication successful.")
    else:
        logger.error("Authentication failed.")
    return token


@retry(max_attempts=3, retry_delay_seconds=5)
def batch_create(counts: Dict, bearer_token: str = None, username: str = None, password: str = None) -> Optional[int]:
    url = settings.HAPI_BATCH_CREATE_URL
    bearer_token = bearer_token or authenticate(username, password)

    headers = {"Authorization": f"Bearer {bearer_token}"}

    response = requests.post(url, json=counts, headers=headers)
    response.raise_for_status()
    return response.json()["batch_id"]


@retry(max_attempts=3, retry_delay_seconds=5)
def batch_submit(bearer_token: str = None, username: str = None, password: str = None, batch_id: int = None, records: List = None) -> bool:
    url = settings.HAPI_BATCH_SUBMIT_URL
    bearer_token = bearer_token or authenticate(username, password)

    headers = {"Authorization": f"Bearer {bearer_token}"}
    payload = {"batch_id": batch_id, "records": records}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 422:
        response.raise_for_status()
    return response.status_code, response.reason, response.text


@retry(max_attempts=3, retry_delay_seconds=5)
def batch_finalise(bearer_token: str = None, username: str = None, password: str = None, batch_id: int = None) -> Optional[int]:
    url = settings.HAPI_BATCH_FINALISE_URL
    bearer_token = bearer_token or authenticate(username, password)

    headers = {"Authorization": f"Bearer {bearer_token}"}
    payload = {"batch_id": batch_id}

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.status_code
