"""
Batch filer — submit multiple FOIA/RTI requests across agencies in one operation.

Supports parallel generation, validation, dry-run preview, and
integrated tracking via TrackerDB.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from foia_rti.generators.generator_base import GeneratedRequest, RequestContext
from foia_rti.generators.us_federal import USFederalGenerator
from foia_rti.generators.us_state import USStateGenerator
from foia_rti.generators.india_rti import IndiaRTIGenerator
from foia_rti.generators.uk_foi import UKFOIGenerator
from foia_rti.generators.eu_requests import EURequestGenerator
from foia_rti.filers.email_filer import EmailFiler, EmailConfig
from foia_rti.tracker.tracker import TrackerDB, RequestStatus
from foia_rti.tracker.deadlines import DeadlineCalculator


@dataclass
class BatchTarget:
    """A single agency target in a batch filing."""

    agency: str
    jurisdiction: str
    topic: str
    specific_records: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    facilities: list[str] = field(default_factory=list)
    template_id: Optional[str] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None


@dataclass
class BatchResult:
    """Result of a single filing within a batch."""

    target: BatchTarget
    success: bool
    request: Optional[GeneratedRequest] = None
    tracker_id: Optional[int] = None
    email_result: Optional[dict[str, str]] = None
    error: Optional[str] = None


class BatchFiler:
    """
    File FOIA/RTI requests to multiple agencies in a single batch.

    Usage:
        targets = [
            BatchTarget(agency="USDA-APHIS", jurisdiction="US-Federal",
                        topic="Inspection reports", ...),
            BatchTarget(agency="EPA", jurisdiction="US-Federal",
                        topic="CAFO permits", ...),
        ]
        filer = BatchFiler(db=tracker_db, email_config=config)
        results = filer.file_batch(targets, requester_name="Org Name")
    """

    GENERATORS = {
        "US-Federal": USFederalGenerator,
        "India": IndiaRTIGenerator,
        "UK": UKFOIGenerator,
        "EU": EURequestGenerator,
    }

    def __init__(
        self,
        db: Optional[TrackerDB] = None,
        email_config: Optional[EmailConfig] = None,
        delay_seconds: float = 2.0,
    ) -> None:
        self.db = db
        self.email_filer = EmailFiler(email_config) if email_config else None
        self.delay_seconds = delay_seconds
        self.deadline_calc = DeadlineCalculator()
        self._generator_cache: dict[str, Any] = {}

    def file_batch(
        self,
        targets: list[BatchTarget],
        requester_name: str = "Open Paws Research",
        requester_org: str = "Open Paws",
        requester_email: str = "",
        requester_address: str = "",
        dry_run: bool = False,
    ) -> list[BatchResult]:
        """
        Generate and optionally file all requests in the batch.

        Args:
            targets: List of agencies/jurisdictions to file with.
            requester_name: Name of the requester.
            requester_org: Organization name.
            requester_email: Contact email.
            requester_address: Mailing address.
            dry_run: If True, generate requests but do not send emails or create DB records.

        Returns:
            List of BatchResult objects, one per target.
        """
        results: list[BatchResult] = []

        for i, target in enumerate(targets):
            try:
                # Build context
                context = RequestContext(
                    agency=target.agency,
                    topic=target.topic,
                    jurisdiction=target.jurisdiction,
                    requester_name=requester_name,
                    requester_organization=requester_org,
                    requester_email=requester_email,
                    requester_address=requester_address,
                    date_range_start=target.date_range_start,
                    date_range_end=target.date_range_end,
                    specific_records=target.specific_records,
                    keywords=target.keywords,
                    facilities=target.facilities,
                    template_id=target.template_id,
                )

                # Generate the request
                generator = self._get_generator(target.jurisdiction)
                generated = generator.generate(context)

                result = BatchResult(target=target, success=True, request=generated)

                # Track in database
                if self.db and not dry_run:
                    filed_date = date.today()
                    deadline = self.deadline_calc.calculate(
                        target.jurisdiction, filed_date
                    )
                    req = self.db.create_request(
                        agency=generated.agency,
                        jurisdiction=generated.jurisdiction,
                        topic=target.topic,
                        request_text=generated.text,
                        date_filed=filed_date,
                        deadline=deadline,
                        status=RequestStatus.FILED,
                        filing_method=generated.filing_method,
                        fee_waiver_requested=True,
                    )
                    result.tracker_id = req.id

                # Send via email
                if self.email_filer:
                    try:
                        msg = self.email_filer.format_request(generated)
                        email_result = self.email_filer.send(msg, dry_run=dry_run)
                        result.email_result = email_result
                    except ValueError as e:
                        result.email_result = {"status": "skipped", "reason": str(e)}

                results.append(result)

                # Rate limiting between filings
                if i < len(targets) - 1 and not dry_run:
                    time.sleep(self.delay_seconds)

            except Exception as e:
                results.append(
                    BatchResult(target=target, success=False, error=str(e))
                )

        return results

    def preview_batch(
        self,
        targets: list[BatchTarget],
        requester_name: str = "Open Paws Research",
    ) -> list[dict[str, Any]]:
        """Generate previews of all requests without filing."""
        results = self.file_batch(
            targets,
            requester_name=requester_name,
            dry_run=True,
        )
        previews = []
        for r in results:
            preview = {
                "agency": r.target.agency,
                "jurisdiction": r.target.jurisdiction,
                "topic": r.target.topic,
                "success": r.success,
            }
            if r.request:
                preview["text_preview"] = r.request.text[:500] + "..."
                preview["legal_basis"] = r.request.legal_basis
                preview["deadline_days"] = r.request.estimated_deadline_days
                preview["filing_method"] = r.request.filing_method
            if r.error:
                preview["error"] = r.error
            previews.append(preview)
        return previews

    def _get_generator(self, jurisdiction: str):
        """Get or create a generator for the given jurisdiction."""
        # Normalize state jurisdictions
        gen_key = jurisdiction
        if jurisdiction.startswith("US-State"):
            gen_key = "US-State"

        if gen_key not in self._generator_cache:
            if gen_key == "US-State":
                self._generator_cache[gen_key] = USStateGenerator()
            elif gen_key in self.GENERATORS:
                self._generator_cache[gen_key] = self.GENERATORS[gen_key]()
            else:
                raise ValueError(f"No generator for jurisdiction '{jurisdiction}'")

        return self._generator_cache[gen_key]
