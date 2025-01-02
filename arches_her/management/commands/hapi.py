'''
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

from django.core.management.base import BaseCommand
from django.db import connection
from arches.app.models.system_settings import settings
from pathlib import Path
from ...data_access.common import (
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
from ...data_access.monument import (
    call_get_monument_dated_types,
    get_monument_sources
)
from ...models.factory import create_resource
from typing import Dict, List, Optional
import logging
import uuid
import os
import json
import decimal
from datetime import datetime
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import re
from colorama import Fore, init
from ...services import validate as validate_service
from ...services import authenticate as authenticate_service
from ...services import batch_create as batch_create_service

logger = logging.getLogger(__name__)
init(autoreset=True)

# Utility Functions


def parse_postgresql_interval(interval: str) -> relativedelta:
    """
    Parses a PostgreSQL interval string and converts it to a relativedelta object.

    Args:
        interval (str): The interval string in PostgreSQL format (e.g., "1 year 3 hours 20 minutes").

    Returns:
        relativedelta: A relativedelta object representing the parsed interval.

    Raises:
        ValueError: If the interval format is invalid or contains unsupported units.

    Example:
        >>> interval = "1 year 3 hours 20 minutes"
        >>> delta = parse_postgresql_interval(interval)
        >>> print(delta)
        relativedelta(years=+1, hours=+3, minutes=+20)
    """
    pattern = r"(\d+)\s*(day|days|week|weeks|month|months|year|years|hour|hours|minute|minutes|second|seconds)"
    matches = re.findall(pattern, interval)
    if not matches:
        raise ValueError(f"Invalid interval format: {interval}")

    delta = relativedelta()
    unit_mapping = {
        'day': 'days', 'days': 'days',
        'week': 'weeks', 'weeks': 'weeks',
        'month': 'months', 'months': 'months',
        'year': 'years', 'years': 'years',
        'hour': 'hours', 'hours': 'hours',
        'minute': 'minutes', 'minutes': 'minutes',
        'second': 'seconds', 'seconds': 'seconds'
    }

    for value, unit in matches:
        value = int(value)
        if unit in unit_mapping:
            kwargs = {unit_mapping[unit]: value}
            delta += relativedelta(**kwargs)
        else:
            raise ValueError(f"Unsupported interval unit: {unit}")

    return delta


def parse_date(date_str: str) -> datetime:
    """
    Parses a date string and converts it to a datetime object.

    Args:
        date_str (str): The date string to parse.

    Returns:
        datetime: The corresponding datetime object.
    """
    if not date_str:
        return None
    if date_str.count(":") == 2:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    elif date_str.count(":") == 1:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    else:
        return datetime.strptime(date_str, "%Y-%m-%d")


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

# Command Class


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            nargs="?",
            choices=["upload", "validate", "generate", "authenticate", "batch_create"],
        )
        parser.add_argument(
            "-u", "--uuid",
            action="store",
            dest="resource_uuid",
            default="",
            help="UUID of resource to process. If providing multiple UUIDs, separate them with a comma.",
        )
        parser.add_argument(
            "-i", "--input",
            action="store",
            dest="input",
            default="",
            help="Name of the file to use to generate the resource JSON response.",
        )
        parser.add_argument(
            "-o", "--output",
            action="store",
            dest="output",
            default="",
            help="Output filename for the generated JSON response. If not provided, the output will be printed to the console.",
        )
        parser.add_argument(
            "-int", "--interval",
            action="store",
            dest="interval",
            default=None,
            help="Interval for the H.API upload operation, e.g., '1 year 3 hours 20 minutes'.",
        )
        parser.add_argument(
            "-sd", "--start_date",
            action="store",
            dest="start_date",
            default="",
            help="Start date for the H.API upload operation.",
        )
        parser.add_argument(
            "-ed", "--end_date",
            action="store",
            dest="end_date",
            default=timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            help="End date for the H.API upload operation.",
        )
        parser.add_argument(
            "-ic", "--internal_call",
            action="store",
            dest="internal_call",
            type=str,
            help="Internal call (True/False).",
        )
        parser.add_argument(
            "-b", "--batch_id",
            action="store",
            dest="batch_id",
            default=None,
            help="Batch ID",
        )
        parser.add_argument(
            "-user", "--username",
            action="store",
            dest="username",
            default=None,
            help="Username for HAPI authentication",
        )
        parser.add_argument(
            "-pass", "--password",
            action="store",
            dest="password",
            default=None,
            help="Password for HAPI authentication",
        )
        parser.add_argument(
            "-bt", "--bearer_token",
            action="store",
            dest="bearer_token",
            default=None,
            help="Bearer token for HAPI batch creation",
        )
        parser.add_argument(
            "-c", "--count",
            action="store",
            dest="counts",
            default=None,
            help='JSON object for counts e.g. {"total_count": 20, "published_count": 18, "submitted_count": 2}',
        )

    def handle(self, *args, **options):
        operation = options["operation"]
        internal_call = options["internal_call"]
        internal_call = (internal_call.lower() == "true") if internal_call else False
        counts_str = options["counts"]
        counts = {}
        if counts_str:
            try:
                counts = json.loads(counts_str)
            except Exception as e:
                print(f"Error parsing counts: {e}")
                return

        if operation == "validate":
            self.validate(
                resource_uuid=options["resource_uuid"],
                input=options["input"],
                output=options["output"],
                internal_call=internal_call
            )
        elif operation == "upload":
            self.upload(
                interval=options["interval"],
                start_date=options["start_date"],
                end_date=options["end_date"],
                internal_call=internal_call
            )
        elif operation == "generate":
            self.generate(
                resource_uuid=options["resource_uuid"],
                input=options["input"],
                output=options["output"],
                internal_call=internal_call,
                batch_id=options["batch_id"]
            )
        elif operation == "authenticate":
            self.authenticate(
                username=options["username"],
                password=options["password"]
            )
        elif operation == "batch_create":
            self.batch_create(
                counts = counts,
                bearer_token=options["bearer_token"],
                username=options["username"],
                password=options["password"]
            )

    def validate(self, resource_uuid=None, input: str = None, output: str = None, internal_call: bool = False, batch_id: str = None) -> str:
        if (resource_uuid and input) or (not resource_uuid and not input):
            # fmt: off
            print(
                f"{Fore.RED}Specify either resource_uuid {Fore.GREEN}-u {Fore.CYAN}--uuid{Fore.RED} "
                f"or filename {Fore.GREEN}-i {Fore.CYAN}--input{Fore.RED}, but not both.{Fore.RESET}"
            )
            # fmt: on
            return

        data = self.generate(resource_uuid=resource_uuid, input=input, output=output, internal_call=True, batch_id=batch_id, returnData=True)
        result, _ = validate_service(json.loads(data))

        if internal_call:
            self.stdout.write(result)
        elif output:
            print(f"Writing validation results to {output}")
            validate_filename(output)
            result = json.dumps(result, indent=4)
            with open(output, 'w') as file:
                file.write(result)
        else:
            print(result)


    def upload(self, interval=None, start_date=None, end_date=None, internal_call: bool =False) -> None:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        if interval and end_date:
            parsed_interval = parse_postgresql_interval(interval)
            start_date = end_date - parsed_interval
            # fmt: off
            message = (
                f"Uploading data for the last {interval} ({parsed_interval}) "
                f"using a start date of {start_date} and end date of {end_date}"
            )
            # fmt: on
            if internal_call:
                self.stdout.write(message)
            else:
                print(message)
        elif start_date and end_date:
            message = (f"Uploading data from {start_date} to {end_date}")
            if internal_call:
                self.stdout.write(message)
            else:
                print(message)
        else:
            # fmt: off
            message = (
                f"{Fore.RED}Specify either interval {Fore.GREEN}-int {Fore.CYAN}--interval{Fore.RED} "
                f"or start_date {Fore.GREEN}-sd {Fore.CYAN}--start_date{Fore.RED} and end_date "
                f"{Fore.GREEN}-ed {Fore.CYAN}--end_date{Fore.RED}. If end_date is not provided, "
                f"the current date and time will be used.{Fore.RESET}"
            )
            # fmt: on
            if internal_call:
                self.stdout.write(message)
            else:
                print(message)

    def generate(self, resource_uuid=None, input: str = None, output: str = None, internal_call: bool = False, batch_id: str = None, returnData: bool = False) -> Optional[str]:
        """Generate data based on the provided UUID or input file."""
        if (resource_uuid and input) or (not resource_uuid and not input):
            # fmt: off
            print(
                f"{Fore.RED}Specify either resource_uuid {Fore.GREEN}-u {Fore.CYAN}--uuid{Fore.RED} "
                f"or filename {Fore.GREEN}-i {Fore.CYAN}--input{Fore.RED}, but not both.{Fore.RESET}"
            )
            # fmt: on
            return

        if resource_uuid:
            uuid_list = validate_uuids(resource_uuid)
        else:
            validate_filename(input)
            uuid_list = validate_uuids(input)

        data = generate_data(uuid_list, batch_id=batch_id)

        if internal_call and not returnData:
            self.stdout.write(data)
        elif internal_call and returnData:
            return data
        elif output:
            validate_filename(output)
            with open(output, 'w') as file:
                file.write(data)
        else:
            print(data)

    def authenticate(self, username: str, password: str) -> Optional[str]:
        bearer = authenticate_service(username, password)
        print(bearer) if bearer else None

    def batch_create(self, counts: Dict, bearer_token: str = None, username: str = None, password: str = None) -> Optional[int]:
        required_count_keys = {"total_count", "published_count", "submitted_count"}
        if not required_count_keys.issubset(counts.keys()):
            # fmt: off
            print(
                f"{Fore.RED}Counts must contain the following keys: {Fore.GREEN}{', '.join(required_count_keys)}{Fore.RESET}"
            )
            return
        batch_number = batch_create_service(counts, bearer_token, username, password)
        print(batch_number) if batch_number else None