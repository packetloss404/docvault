"""NER plugin for the document processing pipeline."""

import logging

from processing.context import PluginResult, ProcessingContext
from processing.plugins.base import ProcessingPlugin

logger = logging.getLogger(__name__)


class NERPlugin(ProcessingPlugin):
    """Extract named entities from document content.

    Runs after AIPlugin (order=115). Uses spaCy for NER when available,
    falling back to regex patterns defined on EntityType records.
    The plugin is non-fatal: errors are logged but never stop the pipeline.
    """

    name = "NERPlugin"
    order = 115

    def can_run(self, context: ProcessingContext) -> bool:
        from django.conf import settings

        return (
            getattr(settings, "NER_ENABLED", False)
            and bool(context.content and context.content.strip())
            and context.document_id is not None
        )

    def process(self, context: ProcessingContext) -> PluginResult:
        self.update_progress(context, 0.82, "Extracting named entities...")

        try:
            from .constants import SPACY_LABEL_MAP
            from .extraction import (
                extract_entities_regex,
                extract_entities_spacy,
                normalize_entity_value,
            )
            from .models import Entity, EntityType

            # Ensure default entity types exist.
            EntityType.seed_defaults()

            # Build a look-up of enabled entity types keyed by canonical name.
            type_qs = EntityType.objects.filter(enabled=True)
            type_map = {et.name: et for et in type_qs}

            # --- spaCy-based extraction ---
            raw_entities = extract_entities_spacy(context.content)

            # --- Regex-based extraction (always runs, augments spaCy) ---
            regex_entities = extract_entities_regex(context.content, type_qs)
            raw_entities.extend(regex_entities)

            if not raw_entities:
                return PluginResult(
                    success=True,
                    message="No entities found in document",
                )

            # Delete any previously extracted entities for this document so
            # re-processing produces a clean set.
            Entity.objects.filter(document_id=context.document_id).delete()

            created = 0
            seen = set()  # Deduplicate (type, normalised_value)
            for ent in raw_entities:
                # Map spaCy label to our canonical type name.
                canonical = SPACY_LABEL_MAP.get(ent["label"], ent["label"])
                entity_type = type_map.get(canonical)
                if entity_type is None:
                    continue

                normalised = normalize_entity_value(ent["value"], canonical)
                if not normalised:
                    continue

                dedup_key = (canonical, normalised)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                Entity.objects.create(
                    document_id=context.document_id,
                    entity_type=entity_type,
                    value=normalised,
                    raw_value=ent["value"],
                    confidence=1.0,
                    start_offset=ent.get("start", 0),
                    end_offset=ent.get("end", 0),
                )
                created += 1

            logger.info(
                "Extracted %d unique entities for document %s",
                created,
                context.document_id,
            )
            return PluginResult(
                success=True,
                message=f"Extracted {created} entities",
            )

        except Exception as e:
            logger.warning(
                "NER extraction failed for document %s: %s",
                context.document_id,
                e,
            )
            return PluginResult(
                success=True,
                message=f"NER failed (non-fatal): {e}",
            )
