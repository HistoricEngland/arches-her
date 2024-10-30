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
import logging
import uuid

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            nargs="?",
            choices=[
                "upload",
                "validate",
            ],
        )

        parser.add_argument(
            "-u",
            "--uuid",
            action="store",
            dest="resource_uuid",
            default="",
            help="UUID of resource to validate.",
        )

    def handle(self, *args, **options):
        if options["operation"] == "validate":
            self.validate(
                resource_uuid=options["resource_uuid"],
            )

    def validate(self, resource_uuid):
        try:
            if uuid.UUID(resource_uuid):
                print(f"Validating resource {resource_uuid}")
        except ValueError:
            print("Invalid UUID")
