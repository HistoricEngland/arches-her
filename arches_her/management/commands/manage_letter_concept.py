import uuid
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from arches.app.models import models
from arches.app.search.search_engine_factory import SearchEngineInstance as se
from arches.app.search.mappings import CONCEPTS_INDEX

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Idempotently create/update a Letter concept and wire it into the Letters scheme + collection."

    def add_arguments(self, parser):
        parser.add_argument("-ci", "--concept-id", required=True, help="Concept UUID for the letter concept")
        parser.add_argument("-lv", "--label-valueid", required=True, help="Value UUID for prefLabel")
        parser.add_argument("-iv", "--identifier-valueid", required=True, help="Value UUID for identifier")
        parser.add_argument("-l", "--label", required=True, help="Display label, e.g. 'Letter Z - Test'")

        parser.add_argument(
            "-si",
            "--scheme-id",
            default="15c95776-1eda-43de-bdb7-54c32e984379",
            help="Letters concept scheme UUID",
        )
        parser.add_argument(
            "-co",
            "--collection-id",
            default="e49a01b7-c018-4c35-af8b-5641fe1d25b4",
            help="Letters collection UUID used by Letter Type dropdown",
        )
        parser.add_argument(
            "-bu",
            "--base-uri",
            default="http://localhost:8000",
            help="Base URI used in legacy identifier values",
        )

    @staticmethod
    def _as_uuid(value, field_name):
        try:
            return uuid.UUID(value)
        except ValueError as exc:
            raise CommandError(f"Invalid UUID for {field_name}: {value}") from exc

    @staticmethod
    def _index_concept_value(value_obj, top_concept_id):
        """Index a single concept value to ElasticSearch

        Returns:
            bool: True if indexing succeeded, False otherwise
        """
        try:
            doc = {
                "category": "label",
                "conceptid": str(value_obj.concept_id),
                "language": value_obj.language_id,
                "value": value_obj.value,
                "type": value_obj.valuetype_id,
                "id": str(value_obj.valueid),
                "top_concept": str(top_concept_id),
            }
            se.index_data(index=CONCEPTS_INDEX, body=doc, idfield="id")
            return True
        except Exception as e:
            logger.error(f"Failed to index concept value {value_obj.valueid}: {e}")
            return False

    @transaction.atomic
    def handle(self, *args, **options):
        # --- Parse and validate UUIDs ---
        concept_id = self._as_uuid(options["concept_id"], "concept-id")
        label_valueid = self._as_uuid(options["label_valueid"], "label-valueid")
        identifier_valueid = self._as_uuid(options["identifier_valueid"], "identifier-valueid")
        scheme_id = self._as_uuid(options["scheme_id"], "scheme-id")
        collection_id = self._as_uuid(options["collection_id"], "collection-id")

        # --- Validate label ---
        label = options["label"].strip()
        if not label:
            raise CommandError("--label must not be empty")

        # --- Build concept URI ---
        base_uri = options["base_uri"].rstrip("/")
        concept_uri = f"{base_uri}/{concept_id}"

        # --- Ensure scheme + collection exist ---
        if not models.Concept.objects.filter(conceptid=scheme_id).exists():
            raise CommandError(f"Scheme concept not found: {scheme_id}")

        if not models.Concept.objects.filter(conceptid=collection_id).exists():
            raise CommandError(f"Collection concept not found: {collection_id}")

        # --- Create or fetch concept ---
        concept, created = models.Concept.objects.get_or_create(
            conceptid=concept_id,
            defaults={"nodetype_id": "Concept", "legacyoid": concept_uri},
        )

        # --- Update concept fields only if needed ---
        fields_to_update = []

        if concept.nodetype_id != "Concept":
            concept.nodetype_id = "Concept"
            fields_to_update.append("nodetype_id")

        if concept.legacyoid != concept_uri:
            concept.legacyoid = concept_uri
            fields_to_update.append("legacyoid")

        if fields_to_update:
            concept.save(update_fields=fields_to_update)

        # --- Update prefLabel ---
        pref_label_value, _ = models.Value.objects.update_or_create(
            valueid=label_valueid,
            defaults={
                "concept_id": concept_id,
                "valuetype_id": "prefLabel",
                "language_id": "en",
                "value": label,
            },
        )

        # --- Update identifier ---
        identifier_value, _ = models.Value.objects.update_or_create(
            valueid=identifier_valueid,
            defaults={
                "concept_id": concept_id,
                "valuetype_id": "identifier",
                "language_id": "en",
                "value": concept_uri,
            },
        )

        # --- Ensure relations exist ---
        models.Relation.objects.get_or_create(
            conceptfrom_id=scheme_id,
            conceptto_id=concept_id,
            relationtype_id="hasTopConcept",
        )

        models.Relation.objects.get_or_create(
            conceptfrom_id=collection_id,
            conceptto_id=concept_id,
            relationtype_id="member",
        )

        # --- Index concept values to ElasticSearch ---
        # Index with the scheme_id as the top_concept
        pref_indexed = self._index_concept_value(pref_label_value, scheme_id)
        identifier_indexed = self._index_concept_value(identifier_value, scheme_id)

        # --- Output result ---
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} letter concept {concept_id} ({label})"))

        if pref_indexed and identifier_indexed:
            self.stdout.write(
                self.style.SUCCESS(f"Indexed {label_valueid} (prefLabel) and {identifier_valueid} (identifier) to ElasticSearch")
            )
        elif not pref_indexed and not identifier_indexed:
            self.stdout.write(self.style.WARNING(f"Failed to index both values to ElasticSearch. Run: python manage.py es index_concepts"))
        else:
            failed = "prefLabel" if not pref_indexed else "identifier"
            self.stdout.write(self.style.WARNING(f"Failed to index {failed} to ElasticSearch. Run: python manage.py es index_concepts"))
