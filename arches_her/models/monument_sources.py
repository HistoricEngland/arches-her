from typing import Any, Optional
from urllib.parse import quote
from arches_her.hapi.helper import parse_date
from .base_serializable import BaseSerializable


class MonumentSource(BaseSerializable):
    excluded_fields = set()

    def __init__(
        self,
        information_source_title: Optional[str] = None,
        statement_of_authority: Optional[str] = None,
        source_no: Optional[str] = None,
        source_reference: Optional[str] = None,
        date_of_origination: Optional[str] = None,
        source_digital_object_identifier: Optional[str] = None,
        bibliography_footnote_reference: Optional[str] = None,
        source_url: Optional[str] = None,
    ):
        self.informationSourceTitle = information_source_title
        self.statementOfAuthority = statement_of_authority
        self.sourceNo = source_no
        self.sourceReference = source_reference
        self.dateOfOrigination = parse_date(
            date_of_origination) if date_of_origination else None
        self.sourceDigitalObjectIdentifier = source_digital_object_identifier
        self.bibliographyFootnoteReference = bibliography_footnote_reference
        self.sourceUrl = source_url

    @staticmethod
    def _normalize_url(url: Optional[str]) -> Optional[str]:
        """Return a URL token and percent-encode unsafe characters."""
        if not url or not url.strip():
            return None
        # Keep the first whitespace-delimited token as the URL.
        url_token = url.split()[0]
        # Preserve reserved URL syntax while encoding unsafe characters.
        return quote(url_token, safe=":/?#[]@!$&'()*+,;=%")

    @staticmethod
    def _has_content(field: Any) -> bool:
        """Check if a field has meaningful content (not None or whitespace-only)."""
        if field is None:
            return False
        if isinstance(field, str):
            return bool(field.strip())
        return bool(str(field).strip())

    def has_mandatory_fields(self) -> bool:
        """Check if all mandatory fields have content."""
        mandatory_fields = [self.informationSourceTitle,
                            self.statementOfAuthority, self.dateOfOrigination]
        return all(self._has_content(field) for field in mandatory_fields)

    def get_processed_version(self):
        """Get a version with bibliography footnote reference populated based on mandatory field check."""
        processed = MonumentSource(
            information_source_title=self.informationSourceTitle,
            statement_of_authority=self.statementOfAuthority,
            source_no=self.sourceNo,
            source_reference=self.sourceReference,
            date_of_origination=self.dateOfOrigination,
            source_digital_object_identifier=self.sourceDigitalObjectIdentifier,
            bibliography_footnote_reference=self.bibliographyFootnoteReference,
            source_url=self._normalize_url(self.sourceUrl),
        )

        if not processed.has_mandatory_fields():
            available_fields = []

            if self._has_content(processed.statementOfAuthority):
                available_fields.append(
                    str(processed.statementOfAuthority).strip())
            if self._has_content(processed.dateOfOrigination):
                available_fields.append(
                    str(processed.dateOfOrigination).strip())

            unique_fields = []
            seen = set()
            for field in available_fields:
                if field.lower() not in seen:
                    unique_fields.append(field)
                    seen.add(field.lower())

            if unique_fields:
                processed.bibliographyFootnoteReference = "; ".join(
                    unique_fields)
            else:
                processed.bibliographyFootnoteReference = "Historic England"

        return processed

    def __repr__(self):
        return (
            f"MonumentSource(informationSourceTitle={self.informationSourceTitle}, "
            f"statementOfAuthority={self.statementOfAuthority}, sourceNo={self.sourceNo}, "
            f"sourceReference={self.sourceReference}, dateOfOrigination={self.dateOfOrigination}, "
            f"sourceDigitalObjectIdentifier={self.sourceDigitalObjectIdentifier}, "
            f"bibliographyFootnoteReference={self.bibliographyFootnoteReference}, "
            f"sourceUrl={self.sourceUrl})"
        )
