"""
Base class for public records request generation.

Provides the common interface and Jinja2 template rendering engine
used by all jurisdiction-specific generators.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, BaseLoader


@dataclass
class RequestContext:
    """All parameters needed to generate a public records request."""

    agency: str
    topic: str
    jurisdiction: str
    requester_name: str = "Open Paws Research"
    requester_address: str = ""
    requester_email: str = ""
    requester_phone: str = ""
    requester_organization: str = "Open Paws"
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    specific_records: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    facilities: list[str] = field(default_factory=list)
    fee_waiver: bool = True
    expedited_processing: bool = False
    preferred_format: str = "electronic"
    additional_notes: str = ""
    template_id: Optional[str] = None

    @property
    def date_range_str(self) -> str:
        if self.date_range_start and self.date_range_end:
            return (
                f"{self.date_range_start.strftime('%B %d, %Y')} through "
                f"{self.date_range_end.strftime('%B %d, %Y')}"
            )
        elif self.date_range_start:
            return f"from {self.date_range_start.strftime('%B %d, %Y')} to present"
        elif self.date_range_end:
            return f"up to {self.date_range_end.strftime('%B %d, %Y')}"
        return "all available dates"

    @property
    def filing_date(self) -> str:
        return datetime.now().strftime("%B %d, %Y")


@dataclass
class GeneratedRequest:
    """Output of a request generation."""

    text: str
    jurisdiction: str
    agency: str
    legal_basis: str
    estimated_deadline_days: int
    filing_method: str
    fee_notes: str
    context: RequestContext
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "jurisdiction": self.jurisdiction,
            "agency": self.agency,
            "legal_basis": self.legal_basis,
            "estimated_deadline_days": self.estimated_deadline_days,
            "filing_method": self.filing_method,
            "fee_notes": self.fee_notes,
            "metadata": self.metadata,
        }


class RequestGenerator(ABC):
    """
    Abstract base class for all jurisdiction-specific request generators.

    Subclasses must implement:
        - generate(): produce a GeneratedRequest from a RequestContext
        - get_agencies(): return known agencies for the jurisdiction
        - get_legal_basis(): return the statutory citation
    """

    TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

    def __init__(self, templates_file: Optional[str] = None):
        self._jinja_env = Environment(
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        self._templates: dict[str, Any] = {}
        if templates_file:
            self._load_templates(templates_file)

    def _load_templates(self, filename: str) -> None:
        filepath = self.TEMPLATES_DIR / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                self._templates = json.load(f)

    def _render(self, template_str: str, context: RequestContext, **extra: Any) -> str:
        template = self._jinja_env.from_string(template_str)
        ctx_vars = {
            "ctx": context,
            "agency": context.agency,
            "topic": context.topic,
            "date_range": context.date_range_str,
            "filing_date": context.filing_date,
            "requester_name": context.requester_name,
            "requester_org": context.requester_organization,
            "requester_address": context.requester_address,
            "requester_email": context.requester_email,
            "requester_phone": context.requester_phone,
            "specific_records": context.specific_records,
            "keywords": context.keywords,
            "facilities": context.facilities,
            "preferred_format": context.preferred_format,
            "additional_notes": context.additional_notes,
        }
        ctx_vars.update(extra)
        return template.render(**ctx_vars)

    def get_template(self, template_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a pre-built template by ID from the loaded templates file."""
        templates_list = self._templates.get("templates", [])
        for t in templates_list:
            if t.get("id") == template_id:
                return t
        return None

    def list_templates(self) -> list[dict[str, str]]:
        """Return a summary list of all available templates."""
        return [
            {"id": t["id"], "name": t["name"], "description": t.get("description", "")}
            for t in self._templates.get("templates", [])
        ]

    @abstractmethod
    def generate(self, context: RequestContext) -> GeneratedRequest:
        """Generate a complete public records request."""
        ...

    @abstractmethod
    def get_agencies(self) -> dict[str, dict[str, str]]:
        """Return a dict of known agencies with contact info."""
        ...

    @abstractmethod
    def get_legal_basis(self) -> str:
        """Return the primary statutory citation for this jurisdiction."""
        ...

    @abstractmethod
    def get_fee_waiver_language(self, context: RequestContext) -> str:
        """Return fee waiver request text appropriate to the jurisdiction."""
        ...

    @abstractmethod
    def get_appeal_info(self) -> dict[str, str]:
        """Return information about the appeals process."""
        ...
