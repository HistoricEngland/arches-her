import uuid
import decimal
import html
import logging
import re
from django.db import connection
from typing import Any, List, Optional, Tuple, Union
from collections import OrderedDict
from datetime import datetime
from django.utils import timezone
from django.utils.html import strip_tags
from arches_her.models.monument_dated_types import MonumentDatedTypes
from arches_her.models.historic_aircraft_data import HistoricAircraftData
from arches_her.models.maritime_craft import MaritimeCraft
from arches_her.models.object_finds import ObjectFinds
from arches_her.models.point_geometry import PointGeometry
from arches_her.models.complex_geometry import ComplexGeometry
from arches_her.models.descriptions import Description
from arches_her.models.related_monument_records import RelatedMonumentRecord
from arches_her.models.images import Image
from arches_her.models.related_events import RelatedEvent

logger = logging.getLogger(__name__)


def get_resources(
    interval_param: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resource_instance_ids: Optional[List[uuid.UUID]] = None,
    seed: bool = False
):
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        params = []
        if not seed:
            query = "SELECT * FROM hapi.get_resources("
            if interval_param:
                query += "interval_param := %s, "
                params.append(f"interval '{interval_param}'")

            if start_date:
                if not end_date:
                    end_date = timezone.now()
                query += "start_date := %s, end_date := %s, "
                params.extend([start_date, end_date])

            if resource_instance_ids:
                resource_ids_str = ','.join([str(rid)
                                            for rid in resource_instance_ids])
                query += "resource_instance_ids := %s, "
                params.append(resource_ids_str)

            # Remove the trailing comma and space, and close the function call
            query = query.rstrip(', ') + ");"
        else:
            query = "SELECT * FROM hapi.initial_seed;"
        # Execute the query
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return results


def convert_empty_array_to_none(array):
    return None if array == [] else array


def serialize(obj: Any) -> Union[OrderedDict, List[Any], Tuple[Any, ...], str, int, float, bool, None]:
    # logger.debug(f"Serializing {obj} ({type(obj)})")
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
    elif isinstance(obj, (uuid.UUID, decimal.Decimal, datetime)):
        # Convert specific types to string
        # logger.error(f"Converting {obj} to string")
        return str(obj)
    # Return other primitive types (e.g., int, str) as-is
    # logger.error(f"Returning {obj} as is ({type(obj)})")
    return obj


def generate_json(data: Any) -> Union[OrderedDict, List[Any], Tuple[Any, ...], str, int, float, bool, None]:
    processed_data = serialize(data)
    return processed_data


def get_descriptions(resource_instance_id: uuid.UUID) -> Optional[List[Description]]:
    descriptions = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.descriptions WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()

        for row in rows:
            _, description, type = row
            descriptions.append(Description(
                description=description, type=type))

    return descriptions if descriptions else None


def get_point_geometry(resource_instance_id: uuid.UUID) -> Optional[PointGeometry]:
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.point_geometry WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            _, x_coordinate, y_coordinate = row
            return PointGeometry(x_coordinate=float(x_coordinate), y_coordinate=float(y_coordinate))
        else:
            return None


def get_complex_geometry(resource_instance_id: uuid.UUID) -> Optional[List[ComplexGeometry]]:
    with connection.cursor() as cursor:
        complex_geometry = []
        # Construct the SQL query based on the provided parameters
        query = 'SELECT * FROM hapi.complex_geometry WHERE resourceinstanceid = %s;'
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            _, spatial_feature_type, spatial_feature_geometry = row
            complex_geometry.append(ComplexGeometry(
                spatial_feature_type=spatial_feature_type, spatial_feature_geometry=spatial_feature_geometry))
        return complex_geometry if complex_geometry else None


def get_monument_dated_types(resource_instance_id: uuid.UUID) -> Optional[List[MonumentDatedTypes]]:
    monument_dated_types = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.monument_dated_types WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, types, start_date, end_date, display_date, periods, materials, evidences = row
            for _type in types:
                monument_dated_types.append(MonumentDatedTypes(
                    type=_type,
                    start_date=start_date,
                    end_date=end_date,
                    display_date=display_date,
                    periods=convert_empty_array_to_none(periods),
                    materials=convert_empty_array_to_none(materials),
                    evidences=convert_empty_array_to_none(evidences)
                ))

    return monument_dated_types if monument_dated_types else None


def get_object_finds(resource_instance_id: uuid.UUID) -> Optional[List[ObjectFinds]]:
    object_finds = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.object_finds WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, _, artefact_types, from_date, end_date, cultural_periods, materials = row
            for _type in artefact_types:
                object_finds.append(ObjectFinds(
                    type=_type,
                    start_date=from_date,
                    end_date=end_date,
                    periods=convert_empty_array_to_none(cultural_periods),
                    materials=convert_empty_array_to_none(materials)
                ))

    return object_finds if object_finds else None


def get_maritime_craft(resource_instance_id: uuid.UUID) -> Optional[List[MaritimeCraft]]:
    with connection.cursor() as cursor:
        maritime_craft = []
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.maritime_craft WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, types, start_date, end_date, display_date, periods, main_materials, covering_materials = row
            materials = main_materials + covering_materials
            for _type in types:
                maritime_craft.append(MaritimeCraft(
                    type=_type,
                    start_date=start_date,
                    end_date=end_date,
                    display_date=display_date,
                    periods=convert_empty_array_to_none(periods),
                    materials=convert_empty_array_to_none(materials)
                ))

    return maritime_craft if maritime_craft else None


def get_historic_aircraft(resource_instance_id: uuid.UUID) -> Optional[List[HistoricAircraftData]]:
    with connection.cursor() as cursor:
        historic_aircraft = []
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.historic_aircraft_mv WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, _, types, start_date, end_date, display_date, periods, materials = row
            for _type in types:
                if isinstance(start_date, str) and start_date:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                if isinstance(end_date, str) and end_date:
                    end_date = datetime.strptime(end_date, "%Y-%m-%d")
                historic_aircraft.append(HistoricAircraftData(
                    type=_type,
                    start_date=start_date.strftime(
                        "%Y-%m-%d") if start_date else None,
                    end_date=end_date.strftime(
                        "%Y-%m-%d") if end_date else None,
                    display_date=display_date,
                    periods=convert_empty_array_to_none(periods),
                    materials=convert_empty_array_to_none(materials)
                ))

    return historic_aircraft if historic_aircraft else None


def get_related_monument_records(resource_instance_id: uuid.UUID) -> Optional[List[RelatedMonumentRecord]]:
    with connection.cursor() as cursor:
        related_monument_records = []
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.related_monument_records WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, primary_reference_number, relationship = row
            related_monument_records.append(RelatedMonumentRecord(
                primary_reference_number=primary_reference_number,
                relationship=relationship
            ))

    return related_monument_records if related_monument_records else None


def get_images(resource_instance_id: uuid.UUID) -> Optional[List[Image]]:
    images = []
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.images_mv WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, caption, copyright, url = row
            images.append(Image(
                url=url,
                caption=caption,
                copyright=copyright
            ))

    return images if images else None


def get_other_statuses(resource_instance_id: uuid.UUID) -> Optional[List[str]]:
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.other_statuses_mv WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        other_statuses = []
        for row in rows:
            _, source, reference, description, url = row
            row_elements = []
            if source and reference:
                row_elements.append(f"{source}: {reference}")
            if description:
                row_elements.append(html.unescape(
                    strip_tags(description)).replace("\n", ""))
            if url:
                row_elements.append(f"URL: {url}")
            if row_elements:
                other_statuses.append('; '.join(row_elements))

    return other_statuses if other_statuses else None


def get_related_events(resource_instance_id: uuid.UUID) -> Optional[List[RelatedEvent]]:
    with connection.cursor() as cursor:
        related_events = []
        # Construct the SQL query based on the provided parameters
        query = "SELECT * FROM hapi.related_events WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            _, primary_reference_number, types, name, description = row
            related_events.append(RelatedEvent(
                primary_reference_number=primary_reference_number,
                types=types,
                name=name,
                description=description
            ))

    return related_events if related_events else None


def get_protected_statuses(resource_instance_id: uuid.UUID) -> Optional[List[str]]:
    with connection.cursor() as cursor:
        # Construct the SQL query based on the provided parameters
        query = "SELECT protectedstatuses FROM hapi.protected_statuses_mv WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()

    if row:
        protected_statuses = row[0]
        return protected_statuses if protected_statuses else None
    return None


def refresh_materialized_views(with_data: bool):
    from arches_her.management.commands.apply_hapi_database_migration import Command as rmv
    rmv.refresh_materialized_views(connection.cursor(), refresh_option="WITH DATA" if with_data else "WITH NO DATA")
