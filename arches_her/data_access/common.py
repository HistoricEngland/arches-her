from django.db import connection
from typing import List, Optional
from collections import OrderedDict
import uuid
import json
import decimal
import datetime


def call_hapi_get_resources(
    interval_param: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resource_instance_ids: Optional[List[uuid.UUID]] = None
):
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_resources("
        params = []
        if interval_param:
            query += "interval_param := %s, "
            params.append(f"interval '{interval_param}'")

        if start_date and end_date:
            query += "start_date := %s, end_date := %s, "
            params.extend([start_date, end_date])

        if resource_instance_ids:
            resource_ids_str = ','.join([str(rid)
                                        for rid in resource_instance_ids])
            query += "resource_instance_ids := %s, "
            params.append(resource_ids_str)

        # Remove the trailing comma and space, and close the function call
        query = query.rstrip(', ') + ");"
        # Execute the query
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return results


def serialize(obj):
    if isinstance(obj, dict):
        # Recursively call serialize on each item in the dictionary, excluding keys that start with "_"
        return OrderedDict(
            (k, serialize(v)) for k, v in obj.items() if not k.startswith("_")
        )
    elif isinstance(obj, list):
        # Recursively call serialize on each item in the list
        return [serialize(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # Handle custom objects by converting them to dictionaries
        return OrderedDict(
            (k, serialize(v)) for k, v in obj.__dict__.items() if not k.startswith("_")
        )
    elif isinstance(obj, (uuid.UUID, decimal.Decimal, datetime.datetime)):
        # Convert specific types to string
        return str(obj)
    # Return other primitive types (e.g., int, str) as-is
    return obj


def generate_json(data):
    processed_data = serialize(data)
    return json.dumps(processed_data, default=serialize, indent=4)
