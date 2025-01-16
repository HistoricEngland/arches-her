import uuid
import json
import decimal
import datetime
import html
from django.db import connection
from typing import List, Optional
from collections import OrderedDict
from django.utils.html import strip_tags
from arches_her.models.monument_dated_types import MonumentDatedTypes
from arches_her.models.monument_sources import MonumentSource


def get_monument_sources(resource_instance_id: uuid.UUID) -> Optional[List[MonumentSource]]:
    sources = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.monument_sources_mv WHERE resourceinstanceid = (%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()

        for row in rows:
            _, information_source_title, statement_of_authority, source_no, source_reference, date_of_origination, source_digital_object_identifier, source_url = row
            if isinstance(statement_of_authority, list):
                statement_of_authority = ', '.join(html.unescape(strip_tags(
                    item)).replace("\n", "") for item in statement_of_authority)

            source_reference_parts = []
            if 'pages' in source_reference:
                source_reference_parts.append(
                    f"pages: {source_reference['pages']}")
            if 'figures' in source_reference:
                source_reference_parts.append(
                    f"figures: {source_reference['figures']}")
            if 'plates' in source_reference:
                source_reference_parts.append(
                    f"plates: {source_reference['plates']}")
            source_reference_str = ', '.join(source_reference_parts)

            sources.append(MonumentSource(
                information_source_title=information_source_title,
                statement_of_authority=statement_of_authority,
                source_no=source_no,
                source_reference=source_reference_str,
                date_of_origination=date_of_origination,
                source_digital_object_identifier=source_digital_object_identifier,
                source_url=source_url
            ))
    return sources if sources else None
