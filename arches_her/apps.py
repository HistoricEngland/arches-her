"""
Keystone Django application configuration.
Handles app initialization and runtime patching of Arches models.
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class KeystoneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "arches_her"
    verbose_name = "Keystone"

    def ready(self):
        """
        Initialize the Keystone application.
        Patches Arches Resource.delete() to capture primary reference numbers on deletion.
        """
        try:
            from arches.app.models.resource import Resource as ArchesResource
            from arches.app.models import models as arches_models
            from arches_her.utils.resource_deletion import (
                capture_primary_reference_on_delete,
                update_delete_editlog_with_primary_reference,
            )

            # Store original delete method
            _original_delete = ArchesResource.delete

            # Replace with wrapper that captures primary reference
            def delete_with_capture(self, user={}, index=True, transaction_id=None):
                """
                Extended delete that captures primary reference number before deletion.
                1. Captures primary reference from current tile data
                2. Calls parent delete() which creates the EditLog row
                3. Updates the EditLog row with captured primary reference
                """
                resource_id = str(self.resourceinstanceid)
                graph_id = self.graph_id

                try:
                    # Extract primary reference while tiles still exist
                    capture_primary_reference_on_delete(self)
                except Exception as e:
                    logger.warning(
                        f"Failed to capture primary reference for resource {resource_id}: {e}")

                # Call original delete (which calls save_edit and removes the resource)
                result = _original_delete(
                    self, user=user, index=index, transaction_id=transaction_id)

                # After deletion, update the EditLog row if we captured a primary reference
                if hasattr(self, "_keystone_primary_reference") and result is True:
                    try:
                        # Get the graph name for the mapping
                        graph = arches_models.GraphModel.objects.get(
                            graphid=graph_id)
                        update_delete_editlog_with_primary_reference(
                            resource_id, self._keystone_primary_reference, graph.name)
                    except Exception as e:
                        logger.warning(
                            f"Failed to update EditLog with primary reference for resource {resource_id}: {e}")

                return result

            # Replace the delete method
            ArchesResource.delete = delete_with_capture
            logger.info(
                "Successfully patched Arches Resource.delete() with primary reference capture")

        except ImportError as e:
            logger.warning(f"Could not patch Arches Resource: {e}")
