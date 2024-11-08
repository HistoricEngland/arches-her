from arches_her.models.monument_dated_types import MonumentDatedTypes
from arches_her.models.monument_sources import MonumentSource

from django.db import connection
from typing import List, Optional
from collections import OrderedDict
import uuid
import json
import decimal
import datetime


def call_hapi_get_monument_sources(resource_instance_id: uuid.UUID) -> Optional[List[MonumentSource]]:
    sources = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_monument_sources(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()

        for row in rows:
            # information_source_title, statement_of_authority, source_no, source_reference, date_of_origination, source_digital_object_identifier, bibliography_footnote_reference, source_url = row
            information_source_title, source_no, bibliography_footnote_reference, source_url = row
            sources.append(MonumentSource(
                information_source_title=information_source_title,
                source_no=source_no,
                bibliography_footnote_reference=bibliography_footnote_reference,
                source_url=source_url
            ))

    return sources if sources else None


def call_get_monument_dated_types(resource_instance_id: uuid.UUID) -> Optional[List[MonumentDatedTypes]]:
    monument_dated_types = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_monument_dated_types(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _type, start_date, end_date, display_date, periods, materials, evidences = row
            monument_dated_types.append(MonumentDatedTypes(
                type=_type,
                start_date=start_date,
                end_date=end_date,
                display_date=display_date,
                periods=periods,
                materials=materials,
                evidences=evidences
            ))

    return monument_dated_types if monument_dated_types else None
