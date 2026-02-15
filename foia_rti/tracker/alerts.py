"""
Alert engine for overdue and upcoming-deadline FOIA/RTI requests.

Generates structured alert objects that can be consumed by
email, Telegram, CLI, or any notification system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from foia_rti.tracker.tracker import FOIARequest, RequestStatus, TrackerDB
from foia_rti.tracker.deadlines import DeadlineCalculator


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    OVERDUE = "overdue"


@dataclass
class Alert:
    """A single alert about a tracked request."""

    request_id: int
    agency: str
    jurisdiction: str
    topic: str
    severity: AlertSeverity
    message: str
    days_remaining: Optional[int]
    deadline: Optional[date]
    suggested_action: str

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "agency": self.agency,
            "jurisdiction": self.jurisdiction,
            "topic": self.topic,
            "severity": self.severity.value,
            "message": self.message,
            "days_remaining": self.days_remaining,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "suggested_action": self.suggested_action,
        }

    def format_text(self) -> str:
        severity_prefix = {
            AlertSeverity.INFO: "[INFO]",
            AlertSeverity.WARNING: "[WARNING]",
            AlertSeverity.URGENT: "[URGENT]",
            AlertSeverity.OVERDUE: "[OVERDUE]",
        }
        prefix = severity_prefix[self.severity]
        return (
            f"{prefix} Request #{self.request_id} — {self.agency}\n"
            f"  Topic: {self.topic}\n"
            f"  {self.message}\n"
            f"  Action: {self.suggested_action}\n"
        )


class AlertEngine:
    """
    Scan tracked requests and generate alerts.

    Usage:
        engine = AlertEngine(db)
        alerts = engine.check_all()
        for alert in alerts:
            print(alert.format_text())
    """

    # Days before deadline to trigger each severity level
    THRESHOLDS = {
        AlertSeverity.INFO: 10,
        AlertSeverity.WARNING: 5,
        AlertSeverity.URGENT: 2,
    }

    def __init__(self, db: TrackerDB) -> None:
        self.db = db
        self.calculator = DeadlineCalculator()

    def check_all(self) -> list[Alert]:
        """Check all active requests and return alerts sorted by severity."""
        alerts: list[Alert] = []

        active_statuses = [
            RequestStatus.FILED,
            RequestStatus.ACKNOWLEDGED,
            RequestStatus.PROCESSING,
            RequestStatus.EXTENDED,
            RequestStatus.APPEALED,
        ]

        for status in active_statuses:
            requests = self.db.list_requests(status=status, limit=10000)
            for req in requests:
                alert = self._check_request(req)
                if alert is not None:
                    alerts.append(alert)

        # Sort: OVERDUE first, then URGENT, WARNING, INFO
        severity_order = {
            AlertSeverity.OVERDUE: 0,
            AlertSeverity.URGENT: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3,
        }
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 99), a.days_remaining or 0))
        return alerts

    def check_overdue(self) -> list[Alert]:
        """Return alerts only for overdue requests."""
        return [a for a in self.check_all() if a.severity == AlertSeverity.OVERDUE]

    def check_upcoming(self, within_days: int = 7) -> list[Alert]:
        """Return alerts for requests with deadlines within N days."""
        return [
            a for a in self.check_all()
            if a.days_remaining is not None and 0 < a.days_remaining <= within_days
        ]

    def _check_request(self, req: FOIARequest) -> Optional[Alert]:
        days_left = req.days_until_deadline()
        effective_deadline = req.extended_deadline or req.deadline

        if days_left is None:
            return None

        if days_left < 0:
            days_overdue = abs(days_left)
            return Alert(
                request_id=req.id,
                agency=req.agency,
                jurisdiction=req.jurisdiction,
                topic=req.topic,
                severity=AlertSeverity.OVERDUE,
                message=(
                    f"Response is {days_overdue} day(s) overdue. "
                    f"Deadline was {effective_deadline.isoformat()}."
                ),
                days_remaining=days_left,
                deadline=effective_deadline,
                suggested_action=self._overdue_action(req),
            )

        if days_left <= self.THRESHOLDS[AlertSeverity.URGENT]:
            severity = AlertSeverity.URGENT
        elif days_left <= self.THRESHOLDS[AlertSeverity.WARNING]:
            severity = AlertSeverity.WARNING
        elif days_left <= self.THRESHOLDS[AlertSeverity.INFO]:
            severity = AlertSeverity.INFO
        else:
            return None

        return Alert(
            request_id=req.id,
            agency=req.agency,
            jurisdiction=req.jurisdiction,
            topic=req.topic,
            severity=severity,
            message=f"Deadline in {days_left} day(s) ({effective_deadline.isoformat()}).",
            days_remaining=days_left,
            deadline=effective_deadline,
            suggested_action=self._upcoming_action(req, days_left),
        )

    @staticmethod
    def _overdue_action(req: FOIARequest) -> str:
        if req.jurisdiction == "US-Federal":
            return (
                "Send a follow-up letter citing 5 U.S.C. Section 552(a)(6)(A). "
                "Consider filing an administrative appeal or contacting OGIS "
                "(ogis@nara.gov). Constructive denial of request may entitle "
                "you to immediate appeal."
            )
        if req.jurisdiction == "India":
            return (
                "File a first appeal under Section 19(1) of the RTI Act with "
                "the First Appellate Authority. The PIO's failure to respond "
                "within 30 days is deemed a refusal."
            )
        if req.jurisdiction == "UK":
            return (
                "Send a follow-up citing Section 10(1) of FOIA 2000. "
                "Request an internal review. If no response within a reasonable "
                "time, complain to the ICO."
            )
        if req.jurisdiction == "EU":
            return (
                "The institution's silence after 15 working days constitutes "
                "an implied refusal. File a confirmatory application under "
                "Article 7(2) of Regulation 1049/2001."
            )
        return "Send a follow-up letter and prepare an appeal."

    @staticmethod
    def _upcoming_action(req: FOIARequest, days_left: int) -> str:
        if days_left <= 2:
            return "Prepare appeal materials. Follow up with the agency immediately."
        if days_left <= 5:
            return "Send a courtesy follow-up to the FOIA officer inquiring about status."
        return "Monitor. No action required yet."
