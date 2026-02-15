"""
Dispatch runner — orchestrates multi-persona FOIA/RTI filing campaigns.

Processes dispatch targets in priority order, assigns personas, generates
requests using the existing template system, files via email (or dry-run),
tracks in the database, and produces a dispatch report.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from foia_rti.dispatch.config import (
    DispatchConfig,
    DispatchTarget,
    PersonaAccount,
    load_dispatch_config,
)
from foia_rti.filers.email_filer import EmailConfig, EmailFiler
from foia_rti.generators.generator_base import GeneratedRequest, RequestContext
from foia_rti.generators.india_rti import IndiaRTIGenerator
from foia_rti.generators.us_federal import USFederalGenerator
from foia_rti.tracker.tracker import RequestStatus, TrackerDB


@dataclass
class DispatchResult:
    """Result of dispatching a single target."""

    target: DispatchTarget
    persona_email: str
    persona_name: str
    success: bool
    request_text_preview: str = ""
    agency_full_name: str = ""
    email_result: Optional[dict[str, str]] = None
    tracker_id: Optional[int] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


@dataclass
class DispatchReport:
    """Summary report of a full dispatch run."""

    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    dry_run: bool = False
    total_targets: int = 0
    sent: int = 0
    skipped: int = 0
    failed: int = 0
    results: list[DispatchResult] = field(default_factory=list)

    def summary(self) -> str:
        """Format a human-readable dispatch summary."""
        mode = "DRY RUN" if self.dry_run else "LIVE"
        duration = ""
        if self.completed_at:
            elapsed = (self.completed_at - self.started_at).total_seconds()
            duration = f" in {elapsed:.1f}s"

        lines = [
            f"=== Dispatch Report ({mode}) ===",
            f"Started:  {self.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]
        if self.completed_at:
            lines.append(
                f"Finished: {self.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}{duration}"
            )
        lines.extend([
            f"Targets:  {self.total_targets}",
            f"Sent:     {self.sent}",
            f"Skipped:  {self.skipped}",
            f"Failed:   {self.failed}",
            "",
        ])

        # Per-result details
        for i, r in enumerate(self.results, 1):
            status = "SENT" if r.success else ("SKIP" if r.skipped_reason else "FAIL")
            lines.append(
                f"  [{i:3d}] {status:4s} | P{r.target.priority} | "
                f"{r.target.template_id[:45]:45s} | "
                f"{r.persona_email[:30]:30s}"
            )
            if r.skipped_reason:
                lines.append(f"         Reason: {r.skipped_reason}")
            if r.error:
                lines.append(f"         Error: {r.error}")
            if r.tracker_id:
                lines.append(f"         Tracker: #{r.tracker_id}")

        lines.append("")
        lines.append("=== End Report ===")
        return "\n".join(lines)


class DispatchRunner:
    """
    Orchestrate a multi-persona FOIA/RTI dispatch campaign.

    Usage:
        config = load_dispatch_config("dispatch_config.json")
        runner = DispatchRunner(config, db_url="sqlite:///foia_tracker.db")
        report = runner.run(dry_run=True)
        print(report.summary())
    """

    # Map jurisdiction strings to generator classes
    GENERATORS: dict[str, type] = {
        "US-Federal": USFederalGenerator,
        "India": IndiaRTIGenerator,
    }

    def __init__(
        self,
        config: DispatchConfig,
        db_url: str = "sqlite:///foia_tracker.db",
    ) -> None:
        self.config = config
        self.db = TrackerDB(db_url)
        self._generator_cache: dict[str, Any] = {}
        self._sent_today = 0

    def run(
        self,
        dry_run: bool = False,
        max_today: Optional[int] = None,
    ) -> DispatchReport:
        """
        Execute the dispatch campaign.

        Args:
            dry_run: If True, generate all requests and show what would be
                     sent without actually sending emails or creating DB records.
            max_today: Override the global_max_daily limit for this run.

        Returns:
            A DispatchReport summarizing the entire run.
        """
        daily_limit = max_today if max_today is not None else self.config.global_max_daily
        delay_seconds = self.config.min_delay_minutes * 60

        # Check if today is a weekend and stagger_days is enabled
        if self.config.stagger_days and not dry_run:
            today_weekday = datetime.utcnow().weekday()
            if today_weekday >= 5:  # Saturday=5, Sunday=6
                report = DispatchReport(dry_run=dry_run)
                report.completed_at = datetime.utcnow()
                report.total_targets = len(self.config.targets)
                report.skipped = report.total_targets
                for target in self.config.targets:
                    report.results.append(DispatchResult(
                        target=target,
                        persona_email="",
                        persona_name="",
                        success=False,
                        skipped_reason="Weekend — stagger_days is enabled",
                    ))
                return report

        report = DispatchReport(dry_run=dry_run)
        sorted_targets = self.config.targets_by_priority()
        report.total_targets = len(sorted_targets)

        for i, target in enumerate(sorted_targets):
            # Check global daily limit
            if self._sent_today >= daily_limit:
                result = DispatchResult(
                    target=target,
                    persona_email="",
                    persona_name="",
                    success=False,
                    skipped_reason=f"Daily limit reached ({daily_limit})",
                )
                report.skipped += 1
                report.results.append(result)
                continue

            # Find an available persona for this jurisdiction
            persona = self.config.get_available_persona(target.jurisdiction)
            if persona is None:
                result = DispatchResult(
                    target=target,
                    persona_email="",
                    persona_name="",
                    success=False,
                    skipped_reason=(
                        f"No available persona for jurisdiction '{target.jurisdiction}' "
                        "(all exhausted or inactive)"
                    ),
                )
                report.skipped += 1
                report.results.append(result)
                continue

            # Dispatch this target with the selected persona
            result = self._dispatch_one(target, persona, dry_run=dry_run)
            report.results.append(result)

            if result.success:
                report.sent += 1
                self._sent_today += 1
                persona.record_filing()
            elif result.error:
                report.failed += 1
            else:
                report.skipped += 1

            # Inter-send delay (skip for dry-run and last item)
            if not dry_run and i < len(sorted_targets) - 1 and result.success:
                time.sleep(delay_seconds)

        report.completed_at = datetime.utcnow()
        return report

    def _dispatch_one(
        self,
        target: DispatchTarget,
        persona: PersonaAccount,
        dry_run: bool = False,
    ) -> DispatchResult:
        """Generate, file, and track a single dispatch target."""
        result = DispatchResult(
            target=target,
            persona_email=persona.email,
            persona_name=persona.display_name,
            success=False,
        )

        try:
            # --- Generate the request ---
            generated = self._generate_request(target, persona)
            result.agency_full_name = generated.agency
            result.request_text_preview = generated.text[:300]

            # --- Build email config for this persona ---
            email_config = EmailConfig(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                use_tls=True,
                username=persona.email,
                password=persona.app_password,
                from_address=persona.email,
                from_name=persona.display_name,
                reply_to=persona.email,
            )

            # --- Format and send via EmailFiler ---
            filer = EmailFiler(email_config)
            email_msg = filer.format_request(generated)
            email_result = filer.send(email_msg, dry_run=dry_run)
            result.email_result = email_result

            if email_result.get("status") in ("sent", "dry_run"):
                result.success = True
            else:
                result.error = email_result.get("error", "Unknown email error")
                return result

            # --- Track in database (skip for dry-run) ---
            if not dry_run:
                from foia_rti.tracker.deadlines import DeadlineCalculator

                filed_date = date.today()
                calc = DeadlineCalculator()
                deadline = calc.calculate(target.jurisdiction, filed_date)

                topic = target.topic_override or generated.context.topic
                req = self.db.create_request(
                    agency=generated.agency,
                    jurisdiction=generated.jurisdiction,
                    topic=topic,
                    request_text=generated.text,
                    date_filed=filed_date,
                    deadline=deadline,
                    status=RequestStatus.FILED,
                    filing_method="email",
                    fee_waiver_requested=True,
                    notes=f"Dispatched via persona: {persona.email}",
                )
                result.tracker_id = req.id

        except Exception as e:
            result.error = str(e)

        return result

    def _generate_request(
        self,
        target: DispatchTarget,
        persona: PersonaAccount,
    ) -> GeneratedRequest:
        """Generate a FOIA/RTI request for the given target and persona."""
        # Parse optional date range
        date_start = _parse_date(target.date_range_start) if target.date_range_start else None
        date_end = _parse_date(target.date_range_end) if target.date_range_end else None

        # Look up the template to get default topic
        generator = self._get_generator(target.jurisdiction)
        template_data = generator.get_template(target.template_id)
        topic = target.topic_override
        if not topic and template_data:
            topic = template_data.get("name", target.template_id)

        context = RequestContext(
            agency=target.agency,
            topic=topic,
            jurisdiction=target.jurisdiction,
            requester_name=persona.display_name,
            requester_organization=persona.organization,
            requester_email=persona.email,
            date_range_start=date_start,
            date_range_end=date_end,
            facilities=target.facilities,
            template_id=target.template_id,
            fee_waiver=True,
        )

        return generator.generate(context)

    def _get_generator(self, jurisdiction: str) -> Any:
        """Get or create a cached generator for the jurisdiction."""
        if jurisdiction not in self._generator_cache:
            gen_class = self.GENERATORS.get(jurisdiction)
            if gen_class is None:
                raise ValueError(
                    f"No generator registered for jurisdiction '{jurisdiction}'. "
                    f"Supported: {list(self.GENERATORS.keys())}"
                )
            self._generator_cache[jurisdiction] = gen_class()
        return self._generator_cache[jurisdiction]


def _parse_date(s: str) -> date:
    """Parse a YYYY-MM-DD string into a date object."""
    return datetime.strptime(s, "%Y-%m-%d").date()
