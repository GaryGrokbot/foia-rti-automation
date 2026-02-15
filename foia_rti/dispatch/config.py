"""
Dispatch configuration model.

Defines the data structures for persona accounts, dispatch targets,
and global dispatch settings. Supports loading from a JSON config file
with passwords sourced from environment variables.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class PersonaAccount:
    """A Gmail persona account used to send FOIA/RTI requests.

    Attributes:
        email: Gmail address for this persona.
        app_password: Gmail App Password (loaded from env var at runtime).
        display_name: Human-readable name shown in the From header.
        organization: The org this persona represents.
        jurisdictions: Which jurisdictions this persona can file in
                       (e.g. ["US-Federal", "India"]).
        max_requests_per_week: Per-persona weekly rate limit.
        filed_this_week: Running count of requests filed this week.
        last_filed: Timestamp of the most recent filing by this persona.
        active: Whether this persona is available for dispatch.
    """

    email: str
    app_password: str
    display_name: str
    organization: str
    jurisdictions: list[str] = field(default_factory=list)
    max_requests_per_week: int = 5
    filed_this_week: int = 0
    last_filed: Optional[datetime] = None
    active: bool = True

    def can_file(self, jurisdiction: str) -> bool:
        """Check if this persona can file in the given jurisdiction."""
        if not self.active:
            return False
        if self.filed_this_week >= self.max_requests_per_week:
            return False
        # Wildcard: empty jurisdictions list means all jurisdictions
        if not self.jurisdictions:
            return True
        return jurisdiction in self.jurisdictions

    def record_filing(self) -> None:
        """Increment the weekly counter and set the last-filed timestamp."""
        self.filed_this_week += 1
        self.last_filed = datetime.utcnow()


@dataclass
class DispatchTarget:
    """A single FOIA/RTI request to be dispatched.

    Attributes:
        template_id: ID of the pre-built template to use (from templates/*.json).
        agency: Agency key (e.g. "USDA-APHIS", "AWBI").
        jurisdiction: Legal jurisdiction (e.g. "US-Federal", "India").
        priority: Dispatch priority (1=high, 2=medium, 3=low).
        topic_override: Override the template's default topic string.
        facilities: Specific facilities to include in the request.
        date_range_start: Start date filter (YYYY-MM-DD string).
        date_range_end: End date filter (YYYY-MM-DD string).
    """

    template_id: str
    agency: str
    jurisdiction: str
    priority: int = 2
    topic_override: str = ""
    facilities: list[str] = field(default_factory=list)
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None


@dataclass
class DispatchConfig:
    """Global dispatch configuration.

    Attributes:
        personas: List of persona accounts available for dispatch.
        targets: List of dispatch targets to process.
        global_max_daily: Total requests across all personas per day.
        min_delay_minutes: Minimum delay between any two email sends.
        stagger_days: Whether to spread dispatch across weekdays only.
    """

    personas: list[PersonaAccount] = field(default_factory=list)
    targets: list[DispatchTarget] = field(default_factory=list)
    global_max_daily: int = 20
    min_delay_minutes: int = 15
    stagger_days: bool = True

    def get_available_persona(self, jurisdiction: str) -> Optional[PersonaAccount]:
        """Return the next available persona that can file in the given jurisdiction.

        Selection prefers the persona with the fewest filings this week
        (round-robin balancing).
        """
        candidates = [p for p in self.personas if p.can_file(jurisdiction)]
        if not candidates:
            return None
        # Pick the persona with the lowest weekly filing count
        return min(candidates, key=lambda p: p.filed_this_week)

    def targets_by_priority(self) -> list[DispatchTarget]:
        """Return targets sorted by priority (1 first)."""
        return sorted(self.targets, key=lambda t: t.priority)

    def active_persona_count(self) -> int:
        """Return the number of active personas."""
        return sum(1 for p in self.personas if p.active)


def load_dispatch_config(config_path: str | Path) -> DispatchConfig:
    """Load a DispatchConfig from a JSON file.

    Persona passwords are loaded from environment variables. The JSON
    file specifies the env var name in the ``password_env`` field for
    each persona entry. If the env var is not set, the persona is
    marked inactive.

    Args:
        config_path: Path to the dispatch config JSON file.

    Returns:
        A fully populated DispatchConfig instance.

    Raises:
        FileNotFoundError: If config_path does not exist.
        json.JSONDecodeError: If the JSON is malformed.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Dispatch config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    # --- Parse personas ---
    personas: list[PersonaAccount] = []
    for entry in raw.get("personas", []):
        password_env = entry.get("password_env", "")
        app_password = os.environ.get(password_env, "") if password_env else ""

        persona = PersonaAccount(
            email=entry["email"],
            app_password=app_password,
            display_name=entry.get("display_name", entry["email"]),
            organization=entry.get("organization", "Open Paws"),
            jurisdictions=entry.get("jurisdictions", []),
            max_requests_per_week=entry.get("max_requests_per_week", 5),
            active=entry.get("active", True),
        )

        # Deactivate if no password available
        if not app_password:
            persona.active = False

        personas.append(persona)

    # --- Parse targets ---
    targets: list[DispatchTarget] = []
    for entry in raw.get("targets", []):
        target = DispatchTarget(
            template_id=entry["template_id"],
            agency=entry["agency"],
            jurisdiction=entry["jurisdiction"],
            priority=entry.get("priority", 2),
            topic_override=entry.get("topic_override", ""),
            facilities=entry.get("facilities", []),
            date_range_start=entry.get("date_range_start"),
            date_range_end=entry.get("date_range_end"),
        )
        targets.append(target)

    # --- Build config ---
    return DispatchConfig(
        personas=personas,
        targets=targets,
        global_max_daily=raw.get("global_max_daily", 20),
        min_delay_minutes=raw.get("min_delay_minutes", 15),
        stagger_days=raw.get("stagger_days", True),
    )
