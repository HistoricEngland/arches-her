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
from arches.app.models.system_settings import settings
from pathlib import Path
from arches_her.data_access.common import call_hapi_get_resources, generate_json
from arches_her.models.factory import create_resource
from typing import List
import logging
import uuid
import os
import json
import decimal
import datetime

logger = logging.getLogger(__name__)

# Utility Functions


def is_valid_uuid(uuid_to_test, version=4):
    """Check if the provided UUID is valid."""
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def validate_uuids(uuid_input):
    if os.path.isfile(uuid_input):
        with open(uuid_input, 'r') as file:
            uuid_list = [line.strip() for line in file.readlines()]
    else:
        uuid_list = [uuid.strip() for uuid in uuid_input.split(',')]

    for u in uuid_list:
        if not is_valid_uuid(u):
            raise ValueError(f"Invalid UUID: {u}")
    return uuid_list


def validate_filename(filename):
    """Validate if the provided filename or path is valid."""
    if not os.path.isfile(filename) and not os.path.isdir(os.path.dirname(filename)):
        raise ValueError(f"Invalid filename or path: {filename}")


def generate_data(uuid_list: List[uuid.UUID]) -> str:
    results = call_hapi_get_resources(resource_instance_ids=uuid_list)
    records = []
    for result in results:
        resource = create_resource(
            resource_type=result["resource_type"],
            resource_instance_id=result["resource_instance_id"],
            primary_reference_number=result["primary_reference_number"],
            heritage_asset_name=result["resource_name"],
            descriptions=None,
            last_updated=result["most_recent_timestamp"]
        )
        records.append(resource.__dict__)
    data = {"batch_id": "BATCH_ID", "records": records}
    json = generate_json(data)
    return json

# Command Class


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            nargs="?",
            choices=["upload", "validate", "generate"],
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

    def handle(self, *args, **options):
        operation = options["operation"]
        if operation == "validate":
            self.validate(resource_uuid=options["resource_uuid"])
        elif operation == "upload":
            self.upload()
        elif operation == "generate":
            self.generate(
                resource_uuid=options["resource_uuid"],
                input=options["input"],
                output=options["output"]
            )

    def validate(self, resource_uuid):
        """Validate the provided UUID."""
        try:
            if uuid.UUID(resource_uuid):
                print(f"Validating resource {resource_uuid}")
        except ValueError:
            print("Invalid UUID")

    def upload(self):
        """Stub for upload operation."""
        pass

    def generate(self, resource_uuid=None, input=None, output=None):
        """Generate data based on the provided UUID or input file."""
        if (resource_uuid and input) or (not resource_uuid and not input):
            raise ValueError(
                "Specify either resource_uuid or filename, but not both.")

        if resource_uuid:
            uuid_list = validate_uuids(resource_uuid)
        else:
            validate_filename(input)
            uuid_list = validate_uuids(input)

        data = generate_data(uuid_list)

        if output:
            validate_filename(output)
            with open(output, 'w') as file:
                file.write(data)
        else:
            print(data)
