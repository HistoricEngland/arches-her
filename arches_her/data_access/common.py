import uuid
import decimal
import html
import logging
import json
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
from arches_her.models.monument_sources import MonumentSource
from arches_her.models.protected_status import ProtectedStatus
from arches_her.models.models import HeritageApiConceptMapping

logger = logging.getLogger(__name__)


def _get_concept_mappings() -> List[Tuple[str, str, bool, Optional[str]]]:
    # Read mappings fresh each call so admin updates apply immediately in long-lived workers.
    return [
        (
            obj.hapi_field,
            obj.source_concept,
            obj.mandatory,
            obj.heritage_gateway_concept,
        )
        for obj in HeritageApiConceptMapping.objects.all()
    ]


def _source_value_matches(current_value: Any, source_value: str) -> bool:
    if current_value == source_value:
        return True

    if isinstance(current_value, str) and isinstance(source_value, str):
        return current_value.strip() == source_value.strip()

    return False


def _is_empty_mapping_target(target_value: Optional[str]) -> bool:
    return target_value is None or (
        isinstance(target_value, str) and target_value.strip() == ""
    )


def _apply_mapping_at_terminal(
    parent: dict,
    key: str,
    source_value: str,
    mandatory: bool,
    target_value: Optional[str],
) -> Tuple[bool, bool]:
    if key not in parent:
        return False, False

    current_value = parent[key]

    if isinstance(current_value, list):
        updated_list = []
        changed = False

        for item in current_value:
            if _source_value_matches(item, source_value):
                changed = True
                if not _is_empty_mapping_target(target_value):
                    updated_list.append(target_value)
            else:
                updated_list.append(item)

        if changed:
            parent[key] = updated_list

        return changed, False

    if _source_value_matches(current_value, source_value):
        if _is_empty_mapping_target(target_value):
            if mandatory:
                return True, True

            parent.pop(key, None)
            return True, False

        parent[key] = target_value
        return True, False

    return False, False


def _apply_mapping_for_path(
    current: Any,
    path_parts: List[str],
    path_index: int,
    source_value: str,
    mandatory: bool,
    target_value: Optional[str],
) -> Tuple[bool, bool]:
    if isinstance(current, list):
        changed = False
        retained_items = []

        for item in current:
            item_changed, remove_item = _apply_mapping_for_path(
                item,
                path_parts,
                path_index,
                source_value,
                mandatory,
                target_value,
            )
            changed = changed or item_changed
            if not remove_item:
                retained_items.append(item)

        if len(retained_items) != len(current):
            changed = True
            current[:] = retained_items

        return changed, False

    if not isinstance(current, dict):
        return False, False

    path_key = path_parts[path_index]
    if path_key not in current:
        return False, False

    if path_index == len(path_parts) - 1:
        return _apply_mapping_at_terminal(
            current,
            path_key,
            source_value,
            mandatory,
            target_value,
        )

    next_value = current[path_key]
    changed, remove_current = _apply_mapping_for_path(
        next_value,
        path_parts,
        path_index + 1,
        source_value,
        mandatory,
        target_value,
    )

    if remove_current:
        if isinstance(next_value, list):
            current[path_key] = []
        else:
            current.pop(path_key, None)
        changed = True

    return changed, False


def _apply_mapping_for_path_anywhere(
    current: Any,
    path_parts: List[str],
    source_value: str,
    mandatory: bool,
    target_value: Optional[str],
) -> bool:
    changed = False

    applied_here, _ = _apply_mapping_for_path(
        current=current,
        path_parts=path_parts,
        path_index=0,
        source_value=source_value,
        mandatory=mandatory,
        target_value=target_value,
    )
    changed = changed or applied_here

    if isinstance(current, dict):
        for child in current.values():
            changed = _apply_mapping_for_path_anywhere(
                current=child,
                path_parts=path_parts,
                source_value=source_value,
                mandatory=mandatory,
                target_value=target_value,
            ) or changed
    elif isinstance(current, list):
        for item in current:
            changed = _apply_mapping_for_path_anywhere(
                current=item,
                path_parts=path_parts,
                source_value=source_value,
                mandatory=mandatory,
                target_value=target_value,
            ) or changed

    return changed


def _prune_empty_containers(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = OrderedDict()
        for key, item in value.items():
            pruned = _prune_empty_containers(item)
            if pruned not in (None, [], {}):
                cleaned[key] = pruned
        return cleaned

    if isinstance(value, list):
        cleaned_list = [_prune_empty_containers(item) for item in value]
        return [item for item in cleaned_list if item not in (None, [], {})]

    return value


def _apply_concept_mappings_to_json(data: Any) -> Any:
    concept_mappings = _get_concept_mappings()
    if not concept_mappings:
        return data

    for hapi_field, source_concept, mandatory, gateway_concept in concept_mappings:
        if not hapi_field or source_concept is None:
            continue

        path_parts = [part.strip()
                      for part in hapi_field.split(".") if part.strip()]
        if not path_parts:
            continue

        _apply_mapping_for_path_anywhere(
            current=data,
            path_parts=path_parts,
            source_value=source_concept,
            mandatory=mandatory,
            target_value=gateway_concept,
        )

    return _prune_empty_containers(data)


def get_resources(
    interval_param: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resource_instance_ids: Optional[List[uuid.UUID]] = None,
    seed: bool = False,
    seed_limit_count: int = 0,
):
    with connection.cursor() as cursor:
        params = []
        func_args = []

        if not seed:
            query = "SELECT * FROM hapi.get_resources("

            if interval_param:
                func_args.append("interval_param := %s::interval")
                params.append(interval_param)

            if start_date:
                if not end_date:
                    end_date = timezone.now().isoformat()
                func_args.append("start_date := %s")
                func_args.append("end_date := %s")
                params.extend([start_date, end_date])

            if resource_instance_ids:
                resource_ids_str = ",".join(
                    [str(rid) for rid in resource_instance_ids])
                func_args.append("resource_instance_ids := %s")
                params.append(resource_ids_str)

            query = f"{query}{', '.join(func_args) if func_args else ''});"
        else:
            if seed_limit_count > 0:
                query = "SELECT * FROM hapi.initial_seed ORDER BY primary_reference_number LIMIT %s;"
                params.append(seed_limit_count)
            else:
                query = "SELECT * FROM hapi.initial_seed ORDER BY primary_reference_number;"

        cursor.execute(query, params)
        if cursor.description is None:
            return []
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return results


def is_empty_or_whitespace(s: str) -> bool:
    return s is None or (isinstance(s, str) and s.strip() == '')


def filtered_string(strings: str) -> Optional[str]:
    return [s.strip() if isinstance(s, str) else s for s in strings if not is_empty_or_whitespace(s)]


def convert_empty_array_to_none(array):
    return None if array == [] else array


def serialize(obj: Any) -> Union[OrderedDict, List[Any], Tuple[Any, ...], str, int, float, bool, None]:
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return serialize(obj.to_dict())
    if isinstance(obj, dict):
        # Recursively call serialize on each item in the dictionary, excluding keys that start with "_" and None values
        return OrderedDict(
            (k, v_serialized)
            for k, v in obj.items()
            if not k.startswith("_")
            and (v_serialized := serialize(v)) not in (None, [], {})
        )
    elif isinstance(obj, list):
        # Recursively call serialize on each item in the list, excluding None values
        return [item for item in (serialize(i) for i in obj) if item is not None]
        # return [serialize(item) for item in obj if item is not None]
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
        return str(obj)
    # Return other primitive types (e.g., int, str) as-is
    return obj


def generate_json(data: Any) -> Union[OrderedDict, List[Any], Tuple[Any, ...], str, int, float, bool, None]:
    processed_data = serialize(data)
    return _apply_concept_mappings_to_json(processed_data)


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
        query = "SELECT x_coordinate, y_coordinate FROM hapi.geometry WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            x_coordinate, y_coordinate = row
            return PointGeometry(x_coordinate=float(x_coordinate), y_coordinate=float(y_coordinate))
        else:
            return None


def get_complex_geometry(resource_instance_id: uuid.UUID) -> Optional[List[ComplexGeometry]]:
    with connection.cursor() as cursor:
        complex_geometry = []
        # Construct the SQL query based on the provided parameters
        query = 'SELECT spatialfeaturetype, spatialfeaturegeometry FROM hapi.geometry WHERE resourceinstanceid = %s;'
        params = [str(resource_instance_id)]

        # Execute the query
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            spatial_feature_type, spatial_feature_geometry = row
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
            description = html.unescape(
                strip_tags(description)).replace("\n", "")
            related_events.append(RelatedEvent(
                primary_reference_number=primary_reference_number,
                types=types,
                name=name,
                description=description
            ))

    return related_events if related_events else None


def get_protected_statuses(resource_instance_id: uuid.UUID) -> Optional[ProtectedStatus]:
    with connection.cursor() as cursor:
        query = "SELECT protectedstatuses FROM hapi.protected_statuses_mv WHERE resourceinstanceid = %s;"
        params = [str(resource_instance_id)]
        cursor.execute(query, params)
        row = cursor.fetchone()

    protected_statuses = ProtectedStatus()
    if row:
        for status in (row[0] or []):
            protected_statuses.protectedStatuses.append(status)

    return protected_statuses if protected_statuses else None


def refresh_materialized_views(with_data: bool):
    from arches_her.management.commands.apply_hapi_database_migration import Command as rmv
    rmv.refresh_materialized_views(connection.cursor(
    ), refresh_option="WITH DATA" if with_data else "WITH NO DATA")


def get_monument_sources(resource_instance_id: uuid.UUID) -> Optional[List[MonumentSource]]:
    """Get raw monument sources (for validation reporting)."""
    sources = []
    with connection.cursor() as cursor:
        query = "SELECT * FROM hapi.monument_sources_mv WHERE resourceinstanceid = (%s);"
        params = [str(resource_instance_id)]

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            sources.append(MonumentSource())

        for row in rows:
            _, information_source_title, statement_of_authority, source_no, source_reference, date_of_origination, source_digital_object_identifier, source_url = row
            if isinstance(source_reference, str):
                source_reference = json.loads(source_reference)
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
            source_reference_str = ', '.join(
                source_reference_parts) if source_reference_parts else None

            sources.append(MonumentSource(
                information_source_title=information_source_title,
                statement_of_authority=statement_of_authority,
                source_no=source_no,
                source_reference=source_reference_str,
                date_of_origination=date_of_origination,
                source_digital_object_identifier=source_digital_object_identifier,
                source_url=source_url,
            ))
    return sources if sources else None


def get_processed_monument_sources(resource_instance_id: uuid.UUID) -> Optional[List[MonumentSource]]:
    """Get processed monument sources with mandatory field validation applied (for API submission)."""
    raw_sources = get_monument_sources(resource_instance_id)
    if not raw_sources:
        return None
    return [source.get_processed_version() for source in raw_sources]


def get_counts():
    """
    Get counts of total records and published records from the database.

    Returns:
        tuple: (total_count, published_count)
    """
    # TODO: Need to work out what total_count and published_count should be
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM hapi.initial_seed) AS total_count,
                (SELECT COUNT(*) FROM hapi.initial_seed) AS published_count
        """)
        result = cursor.fetchone()

    return result if result else (0, 0)
