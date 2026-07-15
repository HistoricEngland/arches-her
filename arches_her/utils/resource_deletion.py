"""
Resource deletion utilities for capturing primary reference numbers.
"""

import logging
from typing import Optional
from arches.app.models import models as arches_models

logger = logging.getLogger(__name__)


# Node UUID mappings for primary reference numbers by resource type
PRIMARY_REFERENCE_NODE_MAPPING = {
    "Monument": "325a2f33-efe4-11eb-b0bb-a87eeabdefba",
    "Maritime Vessel": "f1cbd897-f007-11eb-8b4b-a87eeabdefba",
    "Historic Aircraft": "7f5591c5-efed-11eb-8e44-a87eeabdefba",
}


def get_primary_reference_from_tiles(resource_instance) -> Optional[str]:
    """
    Extract primary reference number from a resource's tile data.

    Queries the resource's tiles and looks for the configured primary reference node
    based on the resource's graph type.

    Args:
        resource_instance: Arches Resource or ResourceInstance

    Returns:
        The primary reference number value, or None if not found
    """
    try:
        graph = arches_models.GraphModel.objects.get(
            graphid=resource_instance.graph_id)
        graph_name = graph.name

        node_uuid = PRIMARY_REFERENCE_NODE_MAPPING.get(graph_name)
        if not node_uuid:
            logger.debug(
                f"No primary reference mapping for resource type: {graph_name}")
            return None

        tiles = arches_models.TileModel.objects.filter(
            resourceinstance_id=resource_instance.resourceinstanceid)

        for tile in tiles:
            if node_uuid in tile.data and tile.data[node_uuid] is not None:
                value = tile.data[node_uuid]
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    value = value[0]
                if value:
                    logger.debug(
                        f"Found primary reference '{value}' for resource " f"{resource_instance.resourceinstanceid} in node {node_uuid}"
                    )
                    return str(value)

        logger.debug(
            f"No primary reference found for resource " f"{resource_instance.resourceinstanceid} in node {node_uuid}")
        return None

    except Exception as e:
        logger.warning(
            f"Error extracting primary reference from tiles for resource " f"{resource_instance.resourceinstanceid}: {e}")
        return None


def capture_primary_reference_on_delete(resource_instance) -> None:
    """
    Capture primary reference number and store it on the resource instance
    before deletion removes its tile data.

    Args:
        resource_instance: Arches Resource being deleted
    """
    try:
        primary_ref = get_primary_reference_from_tiles(resource_instance)

        if primary_ref:
            resource_instance._keystone_primary_reference = primary_ref
            logger.info(
                f"Captured primary reference '{primary_ref}' for deletion of resource " f"{resource_instance.resourceinstanceid}")
        else:
            logger.debug(
                f"No primary reference captured for resource {resource_instance.resourceinstanceid}")

    except Exception as e:
        logger.error(
            f"Critical error capturing primary reference for resource " f"{resource_instance.resourceinstanceid}: {e}")


def update_delete_editlog_with_primary_reference(
    resource_instance_id: str,
    primary_reference: str,
    graph_name: str,
) -> bool:
    """
    Update the most recent delete EditLog row for a resource with primary reference data.

    Args:
        resource_instance_id: UUID of the deleted resource
        primary_reference: The primary reference number to store
        graph_name: Name of the graph/resource type

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        node_uuid = PRIMARY_REFERENCE_NODE_MAPPING.get(graph_name)
        if not node_uuid:
            logger.debug(f"No node mapping for graph {graph_name}")
            return False

        edit_log = (
            arches_models.EditLog.objects.filter(
                resourceinstanceid=resource_instance_id,
                edittype="delete",
            )
            .order_by("-timestamp")
            .first()
        )

        if not edit_log:
            logger.warning(
                f"No delete EditLog found for resource {resource_instance_id}")
            return False

        newvalue = {
            "primary_reference_number": primary_reference,
            node_uuid: primary_reference,
        }

        edit_log.newvalue = newvalue
        edit_log.save(update_fields=["newvalue"])

        logger.info(
            f"Updated delete EditLog for resource {resource_instance_id} " f"with primary reference: {newvalue}")
        return True

    except Exception as e:
        logger.error(
            f"Error updating delete EditLog for resource {resource_instance_id}: {e}")
        return False
