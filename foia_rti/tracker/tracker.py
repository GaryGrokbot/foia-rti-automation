"""
SQLAlchemy models and CRUD operations for tracking FOIA/RTI requests.

Stores every request from filing through final disposition, including
deadlines, responses, documents received, and notes.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class RequestStatus(enum.Enum):
    """Lifecycle states for a public records request."""

    DRAFT = "draft"
    FILED = "filed"
    ACKNOWLEDGED = "acknowledged"
    PROCESSING = "processing"
    EXTENDED = "extended"
    PARTIAL_RESPONSE = "partial_response"
    COMPLETE = "complete"
    DENIED = "denied"
    APPEALED = "appealed"
    APPEAL_WON = "appeal_won"
    APPEAL_DENIED = "appeal_denied"
    LITIGATION = "litigation"
    WITHDRAWN = "withdrawn"
    NO_RESPONSIVE_RECORDS = "no_responsive_records"


class FOIARequest(Base):
    """A single public records request and its lifecycle data."""

    __tablename__ = "foia_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # --- identification ---
    reference_id = Column(String(128), unique=True, nullable=True, index=True)
    agency = Column(String(256), nullable=False, index=True)
    agency_key = Column(String(64), nullable=True)
    jurisdiction = Column(String(64), nullable=False, index=True)
    topic = Column(String(512), nullable=False)
    # --- dates ---
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_filed = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    date_acknowledged = Column(Date, nullable=True)
    date_extended = Column(Date, nullable=True)
    extended_deadline = Column(Date, nullable=True)
    date_response = Column(Date, nullable=True)
    # --- status ---
    status = Column(Enum(RequestStatus), default=RequestStatus.DRAFT, nullable=False, index=True)
    # --- response data ---
    docs_received = Column(Integer, default=0)
    pages_received = Column(Integer, default=0)
    pages_withheld = Column(Integer, default=0)
    exemptions_cited = Column(Text, nullable=True)
    # --- filing info ---
    filing_method = Column(String(64), nullable=True)
    confirmation_number = Column(String(128), nullable=True)
    assigned_analyst = Column(String(128), nullable=True)
    fee_paid = Column(String(64), nullable=True)
    fee_waiver_requested = Column(Boolean, default=True)
    fee_waiver_granted = Column(Boolean, nullable=True)
    # --- content ---
    request_text = Column(Text, nullable=True)
    response_summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    # --- appeal ---
    appeal_filed = Column(Boolean, default=False)
    appeal_date = Column(Date, nullable=True)
    appeal_body = Column(String(256), nullable=True)
    appeal_outcome = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<FOIARequest(id={self.id}, agency='{self.agency}', "
            f"status={self.status.value}, jurisdiction='{self.jurisdiction}')>"
        )

    def is_overdue(self) -> bool:
        if self.status in (
            RequestStatus.COMPLETE,
            RequestStatus.DENIED,
            RequestStatus.WITHDRAWN,
            RequestStatus.NO_RESPONSIVE_RECORDS,
        ):
            return False
        effective_deadline = self.extended_deadline or self.deadline
        if effective_deadline is None:
            return False
        return date.today() > effective_deadline

    def days_until_deadline(self) -> Optional[int]:
        effective_deadline = self.extended_deadline or self.deadline
        if effective_deadline is None:
            return None
        return (effective_deadline - date.today()).days


class TrackerDB:
    """
    CRUD interface for the request tracker database.

    Usage:
        db = TrackerDB("sqlite:///requests.db")
        req = db.create_request(agency="USDA-APHIS", jurisdiction="US-Federal", ...)
        db.update_status(req.id, RequestStatus.FILED, date_filed=date.today())
        overdue = db.get_overdue()
    """

    def __init__(self, db_url: str = "sqlite:///foia_tracker.db") -> None:
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine)

    def _session(self) -> Session:
        return self.SessionFactory()

    # ---- Create ----

    def create_request(
        self,
        agency: str,
        jurisdiction: str,
        topic: str,
        request_text: str = "",
        **kwargs,
    ) -> FOIARequest:
        with self._session() as session:
            req = FOIARequest(
                agency=agency,
                jurisdiction=jurisdiction,
                topic=topic,
                request_text=request_text,
                **kwargs,
            )
            session.add(req)
            session.commit()
            session.refresh(req)
            return req

    # ---- Read ----

    def get_request(self, request_id: int) -> Optional[FOIARequest]:
        with self._session() as session:
            return session.get(FOIARequest, request_id)

    def get_by_reference(self, reference_id: str) -> Optional[FOIARequest]:
        with self._session() as session:
            return (
                session.query(FOIARequest)
                .filter(FOIARequest.reference_id == reference_id)
                .first()
            )

    def list_requests(
        self,
        jurisdiction: Optional[str] = None,
        status: Optional[RequestStatus] = None,
        agency: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FOIARequest]:
        with self._session() as session:
            q = session.query(FOIARequest)
            if jurisdiction:
                q = q.filter(FOIARequest.jurisdiction == jurisdiction)
            if status:
                q = q.filter(FOIARequest.status == status)
            if agency:
                q = q.filter(FOIARequest.agency.ilike(f"%{agency}%"))
            q = q.order_by(FOIARequest.date_created.desc())
            return q.offset(offset).limit(limit).all()

    def get_overdue(self) -> list[FOIARequest]:
        with self._session() as session:
            today = date.today()
            terminal = [
                RequestStatus.COMPLETE,
                RequestStatus.DENIED,
                RequestStatus.WITHDRAWN,
                RequestStatus.NO_RESPONSIVE_RECORDS,
            ]
            return (
                session.query(FOIARequest)
                .filter(
                    FOIARequest.status.notin_(terminal),
                    (
                        (FOIARequest.extended_deadline != None) & (FOIARequest.extended_deadline < today)
                    )
                    | (
                        (FOIARequest.extended_deadline == None) & (FOIARequest.deadline != None) & (FOIARequest.deadline < today)
                    ),
                )
                .all()
            )

    def get_stats(self) -> dict[str, int]:
        with self._session() as session:
            total = session.query(FOIARequest).count()
            by_status: dict[str, int] = {}
            for st in RequestStatus:
                count = session.query(FOIARequest).filter(FOIARequest.status == st).count()
                if count > 0:
                    by_status[st.value] = count
            overdue = len(self.get_overdue())
            return {"total": total, "overdue": overdue, "by_status": by_status}

    # ---- Update ----

    def update_status(
        self, request_id: int, status: RequestStatus, **kwargs
    ) -> Optional[FOIARequest]:
        with self._session() as session:
            req = session.get(FOIARequest, request_id)
            if req is None:
                return None
            req.status = status
            for key, val in kwargs.items():
                if hasattr(req, key):
                    setattr(req, key, val)
            session.commit()
            session.refresh(req)
            return req

    def add_note(self, request_id: int, note: str) -> Optional[FOIARequest]:
        with self._session() as session:
            req = session.get(FOIARequest, request_id)
            if req is None:
                return None
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            entry = f"[{timestamp}] {note}"
            req.notes = f"{req.notes}\n{entry}" if req.notes else entry
            session.commit()
            session.refresh(req)
            return req

    def record_response(
        self,
        request_id: int,
        docs_received: int = 0,
        pages_received: int = 0,
        pages_withheld: int = 0,
        exemptions_cited: str = "",
        response_summary: str = "",
        date_response: Optional[date] = None,
    ) -> Optional[FOIARequest]:
        with self._session() as session:
            req = session.get(FOIARequest, request_id)
            if req is None:
                return None
            req.docs_received = docs_received
            req.pages_received = pages_received
            req.pages_withheld = pages_withheld
            req.exemptions_cited = exemptions_cited
            req.response_summary = response_summary
            req.date_response = date_response or date.today()
            if pages_withheld > 0:
                req.status = RequestStatus.PARTIAL_RESPONSE
            else:
                req.status = RequestStatus.COMPLETE
            session.commit()
            session.refresh(req)
            return req

    # ---- Delete ----

    def delete_request(self, request_id: int) -> bool:
        with self._session() as session:
            req = session.get(FOIARequest, request_id)
            if req is None:
                return False
            session.delete(req)
            session.commit()
            return True
