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

from collections import defaultdict
import logging
import shutil
import uuid
import os
import json
import re
import glob
import time
from django.core.management.base import BaseCommand
from typing import Dict, List, Optional
from datetime import datetime
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from colorama import Fore, init
from arches_her.services import generate as generate_service
from arches_her.services import validate as validate_service
from arches_her.services import authenticate as authenticate_service
from arches_her.services import batch_create as batch_create_service
from django.db import connection

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


# Command Class


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            nargs="?",
            choices=["upload", "validate", "generate",
                     "authenticate", "batch_create", "test", "test_report"],
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
        internal_call = (internal_call.lower() ==
                         "true") if internal_call else False
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
                output=options["output"]
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
                output=options["output"]
            )
        elif operation == "authenticate":
            self.authenticate(
                username=options["username"],
                password=options["password"]
            )
        elif operation == "batch_create":
            self.batch_create(
                counts=counts,
                bearer_token=options["bearer_token"],
                username=options["username"],
                password=options["password"]
            )
        elif operation == "test":
            self.test()
        elif operation == "test_report":
            self.test_report()

    def validate(self, resource_uuid=None, input: str = None, output: str = None) -> str:
        if (resource_uuid and input) or (not resource_uuid and not input):
            # fmt: off
            print(
                f"{Fore.RED}Specify either resource_uuid {Fore.GREEN}-u {Fore.CYAN}--uuid{Fore.RED} "
                f"or filename {Fore.GREEN}-i {Fore.CYAN}--input{Fore.RED}, but not both.{Fore.RESET}"
            )
            # fmt: on
            return

        result = validate_service(
            resource_uuid=resource_uuid, input=input, output=output)
        if result is not None:
            response, status_code = result
            response = json.dumps(response, indent=4)
            if status_code == 200:
                print(f"{Fore.GREEN}{response}{Fore.RESET}")
            elif status_code == 422:
                print(f"{Fore.YELLOW}{response}{Fore.RESET}")
            else:
                print(f"{Fore.RED}{response}{Fore.RESET}")

    def upload(self, interval=None, start_date=None, end_date=None, internal_call: bool = False) -> None:
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

    def generate(self, resource_uuid=None, input: str = None, output: str = None) -> Optional[str]:
        """Generate data based on the provided UUID or input file."""
        if (resource_uuid and input) or (not resource_uuid and not input):
            # fmt: off
            print(
                f"{Fore.RED}Specify either resource_uuid {Fore.GREEN}-u {Fore.CYAN}--uuid{Fore.RED} "
                f"or filename {Fore.GREEN}-i {Fore.CYAN}--input{Fore.RED}, but not both.{Fore.RESET}"
            )
            # fmt: on
            return

        data = generate_service(
            resource_uuid=resource_uuid, input=input, output=output)
        if data:
            print(f"{Fore.GREEN}{json.dumps(data, indent=4)}{Fore.RESET}")

    def authenticate(self, username: str, password: str) -> Optional[str]:
        bearer = authenticate_service(username, password)
        print(bearer) if bearer else None

    def batch_create(self, counts: Dict, bearer_token: str = None, username: str = None, password: str = None) -> Optional[int]:
        required_count_keys = {"total_count",
                               "published_count", "submitted_count"}
        if not required_count_keys.issubset(counts.keys()):
            # fmt: off
            print(
                f"{Fore.RED}Counts must contain the following keys: {Fore.GREEN}{', '.join(required_count_keys)}{Fore.RESET}"
            )
            return
        batch_number = batch_create_service(counts, bearer_token, username, password)
        print(batch_number) if batch_number else None

    def test(self):
        with connection.cursor() as cursor:
            page_size = 100
            offset = 54700
            counter = 1
            wait_duration = 0.5
            test_folder = "/web_root/hapi_test"
            self.setup_test_folder(test_folder)
            while True:
                cursor.execute("""
                    SELECT resource_instance_id
                    FROM hapi.get_resources(interval_param:='10 years'::interval)
                    WHERE resource_type = 'Monument'
                    ORDER BY primary_reference_number
                    LIMIT %s OFFSET %s;                           
                """, (page_size, offset))
                records = cursor.fetchall()
                if not records:
                    break
                self.process_records(records, counter, test_folder)
                offset += page_size
                counter += 1
                time.sleep(wait_duration)
                return

    def setup_test_folder(self, folder_path):
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path)

    def process_records(self, records, counter, test_folder):
        resource_uuids = ",".join([str(record[0]) for record in records])
        result, status_code = validate_service(resource_uuid=resource_uuids)
        counter = str(counter).zfill(5)
        if isinstance(result, dict) and 'response' in result and 'message' in result['response']:
            print(counter, result['response']['message'])
        filename = f"{test_folder}/{counter}.json"
        with open(filename, 'w') as file:
            file.write(json.dumps(result, indent=4))

    def load_json_file(self, file_path):
        with open(file_path, "r") as file:
            return json.load(file)

    def test_report(self):
        file_paths = sorted(glob.glob("/web_root/hapi_test/*.json"))
        all_errors_count = defaultdict(int)

        for file_path in file_paths:
            data = self.load_json_file(file_path)
            errors = data.get("response", {}).get("errors", [])

            for error in errors:
                for _, value in error.items():
                    for key, value in value.items():
                        strip_key = self.strip_dot_number(key)
                        for _value in value:
                            strip_value = self.strip_dot_number(_value)
                            combined_key = (strip_key, strip_value)
                            all_errors_count[combined_key] += 1

        for key, value in sorted(all_errors_count.items()):
            print(f"Key: {key}, Count: {value}")

    def strip_dot_number(self, text):
        return re.sub(r"\.\d+", "", text)

