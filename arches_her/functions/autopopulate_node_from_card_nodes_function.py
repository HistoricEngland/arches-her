import uuid
from arches.app.functions.base import BaseFunction
from arches.app.models.system_settings import settings
from arches.app.models import models
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource
from arches.app.datatypes.datatypes import DataTypeFactory
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection, transaction
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


details = {
    "name": "Auto-populate Node From Card Nodes",
    "type": "node",
    "description": "Auto-populates a Node in a Card with the values from other Nodes within that Card",
    "defaultconfig": {"autopopulate_configs": [], "triggering_nodegroups": []},
    "classname": "AutopopulateNodeFromCardNodes",
    "component": "views/components/functions/autopopulate-node-from-card-nodes-function",
    "functionid": "184332d6-687d-4bcb-ae41-9aeb467fbdad",
}


class AutopopulateNodeFromCardNodes(BaseFunction):
    """
    Populates a target node in a card with values from other nodes in the same card, based on configuration.
    """

    def autopopulate_nodes(self, tile, request, is_function_save_method=True):
        """
        Populates a target node in a card with values from other nodes in the same card, based on configuration.

        Args:
            tile: The Tile object being saved.
            request: The WSGI request object (can be None).
            is_function_save_method: True if called from save(), False otherwise.
        """
        if request is None and is_function_save_method == True:
            return

        tile_nodegroup = tile.nodegroup_id
        stored_configs = self.config["autopopulate_configs"]

        for auto_pop_config in stored_configs:

            node_to_populate = ""
            autopopulated_string = ""
            populating_nodes = {}
            write_to_node = False

            if auto_pop_config["nodegroup"] == tile_nodegroup:

                node_to_populate = auto_pop_config["target_node"]
                autopopulated_string = auto_pop_config["string_template"]
                autopopulate_nodegroup = auto_pop_config["nodegroup"]
                autopopulate_overwrite = auto_pop_config["overwrite"]

                nodes_in_card = models.Node.objects.filter(
                    nodegroup_id=uuid.UUID(autopopulate_nodegroup)
                )

                for card_node in nodes_in_card:
                    if card_node.datatype != "semantic":
                        if card_node.nodeid != node_to_populate:
                            populating_nodes[card_node.nodeid] = card_node.name

                if node_to_populate != "" and autopopulated_string != "":

                    data_in_tile = tile.data

                    try:
                        if node_to_populate in tile.data:

                            if (
                                tile.data[node_to_populate] != None
                                and tile.data[node_to_populate] != ""
                            ):

                                if autopopulate_overwrite != False:
                                    write_to_node = True

                                else:
                                    write_to_node = False

                            else:
                                write_to_node = True

                        else:
                            tile.data[node_to_populate] = ""
                            write_to_node = True

                    except Exception as e:
                        logger.error(
                            f"Error autopopulating node '{node_to_populate}' in tile {tile.pk}: {e}"
                        )

                if write_to_node == True:
                    for n in populating_nodes:
                        node_id_from_card = str(n)
                        node_name_from_card = str(populating_nodes[n])
                        if node_name_from_card in autopopulated_string:
                            node_value_from_tile = ""
                            if node_id_from_card in data_in_tile:
                                try:
                                    node_info = models.Node.objects.get(nodeid=n)
                                    datatype_factory_object = (
                                        DataTypeFactory().get_instance(
                                            node_info.datatype
                                        )
                                    )
                                    node_object = models.Node.objects.get(pk=n)
                                    node_display_value_from_tile = (
                                        datatype_factory_object.get_display_value(
                                            tile, node_object
                                        )
                                    )
                                    if node_display_value_from_tile != None:
                                        node_value_from_tile = (
                                            node_display_value_from_tile
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"Error getting display value for node '{n}' in tile {tile.pk}: {e}"
                                    )

                            try:
                                autopopulated_string = autopopulated_string.replace(
                                    "<%s>" % node_name_from_card, node_value_from_tile
                                )
                            except Exception as e:
                                logger.error(str(e))
                    try:
                        target_node_info = models.Node.objects.get(
                            nodeid=node_to_populate
                        )
                        if target_node_info.datatype == "string":
                            target_datatype = DataTypeFactory().get_instance(
                                target_node_info.datatype
                            )
                            tile.data[node_to_populate] = (
                                target_datatype.transform_value_for_tile(
                                    autopopulated_string
                                )
                            )
                        else:
                            tile.data[node_to_populate] = autopopulated_string
                    except Exception:
                        tile.data[node_to_populate] = autopopulated_string
                    tile.save()
                    return

        return

    def get(self):
        raise NotImplementedError

    def save(self, tile, request, context=None):
        self.autopopulate_nodes(
            tile=tile, request=request, is_function_save_method=True
        )
        return

    def post_save(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, tile, request):
        raise NotImplementedError

    def on_import(self, tile):
        raise NotImplementedError

    def after_function_save(self, tile, request):
        current_config = tile.config if isinstance(tile.config, dict) else {}
        autopopulate_configs = current_config.get("autopopulate_configs") or []

        if not isinstance(autopopulate_configs, list):
            raise ValueError("autopopulate_configs must be a list.")

        seen_nodegroups = set()
        for index, entry in enumerate(autopopulate_configs):
            if not isinstance(entry, dict):
                raise ValueError(f"Config at index {index} must be an object.")

            nodegroup = str(entry.get("nodegroup") or "").strip()
            target_node = str(entry.get("target_node") or "").strip()
            string_template = entry.get("string_template")
            has_template_content = isinstance(string_template, str) and any(
                not char.isspace() for char in string_template
            )

            if not nodegroup or not target_node or not has_template_content:
                raise ValueError(
                    f"Config at index {index} is incomplete. nodegroup, target_node, and string_template are required."
                )

            if nodegroup in seen_nodegroups:
                raise ValueError("Only one auto-populate rule is allowed per card.")

            seen_nodegroups.add(nodegroup)
