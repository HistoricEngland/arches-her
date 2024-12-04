from django.db import connection
from typing import List, Optional
from collections import OrderedDict
import uuid
import json
import decimal
import datetime

from ..models.object_finds import ObjectFinds
from ..models.point_geometry import PointGeometry
from ..models.complex_geometry import ComplexGeometry
from ..models.descriptions import Description


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
        # Recursively call serialize on each item in the dictionary, excluding keys that start with "_" and None values
        return OrderedDict(
            (k, serialize(v)) for k, v in obj.items() if not k.startswith("_") and v is not None
        )
    elif isinstance(obj, list):
        # Recursively call serialize on each item in the list, excluding None values
        return [serialize(item) for item in obj if item is not None]
    elif isinstance(obj, tuple):
        # Handle tuples, excluding (None,)
        return tuple(serialize(item) for item in obj if item is not None)
    elif hasattr(obj, "__dict__"):
        # Handle custom objects by converting them to dictionaries
        return OrderedDict(
            (k, serialize(v)) for k, v in obj.__dict__.items() if not k.startswith("_") and v is not None
        )
    elif isinstance(obj, (uuid.UUID, decimal.Decimal, datetime.datetime)):
        # Convert specific types to string
        return str(obj)
    # Return other primitive types (e.g., int, str) as-is
    return obj


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        return serialize(obj)


def generate_json(data: str) -> str:
    processed_data = serialize(data)
    return json.dumps(processed_data, cls=CustomJSONEncoder, indent=4)


def call_hapi_get_descriptions(resource_instance_id: uuid.UUID) -> Optional[List[Description]]:
    descriptions = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_descriptions(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()

        for row in rows:
            type, description = row
            descriptions.append(Description(
                description=description, type=type))

    return descriptions if descriptions else None


def call_hapi_get_point_geometry(resource_instance_id: uuid.UUID) -> Optional[PointGeometry]:
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_point_geometry(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            x_coordinate, y_coordinate = row
            return PointGeometry(x_coordinate=float(x_coordinate), y_coordinate=float(y_coordinate))
        else:
            return None


def call_hapi_get_complex_geometry(resource_instance_id: uuid.UUID) -> Optional[List[ComplexGeometry]]:
    with connection.cursor() as cursor:
        complex_geometry = []
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_complex_geometry(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            spatial_feature_type, spatial_feature_geometry = row
            complex_geometry.append(ComplexGeometry(
                spatial_feature_type=spatial_feature_type, spatial_feature_geometry=spatial_feature_geometry))
        return complex_geometry if complex_geometry else None


def call_hapi_get_monument_dated_types(resource_instance_id: uuid.UUID):
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_monument_dated_types(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return results

def call_hapi_get_object_finds(resource_instance_id: uuid.UUID):
    object_finds = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi_get_object_finds(%s);"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            artefact_types, from_date, end_date, cultural_periods, materials = row
            for _type in artefact_types:
                object_finds.append(ObjectFinds(
                    type=_type,
                    start_date=from_date,
                    end_date=end_date,
                    periods=cultural_periods,
                    materials=materials
                ))

    return object_finds if object_finds else None
