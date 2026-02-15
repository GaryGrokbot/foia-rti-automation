"""
MuckRock API integration for filing and tracking FOIA requests.

MuckRock (https://www.muckrock.com) is a nonprofit platform that helps
file, track, and share public records requests. This module integrates
with their REST API to file requests and sync tracking data.

API docs: https://www.muckrock.com/api/
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import httpx

from foia_rti.generators.generator_base import GeneratedRequest


MUCKROCK_API_BASE = "https://www.muckrock.com/api_v1"


@dataclass
class MuckRockConfig:
    """Configuration for MuckRock API access."""

    api_token: str
    base_url: str = MUCKROCK_API_BASE
    timeout: float = 30.0
    username: str = ""


@dataclass
class MuckRockFOIA:
    """A FOIA request as represented in MuckRock's system."""

    id: int
    title: str
    status: str
    agency: str
    agency_id: int
    date_submitted: Optional[str]
    date_due: Optional[str]
    date_done: Optional[str]
    tracking_id: Optional[str]
    url: str
    absolute_url: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> MuckRockFOIA:
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            status=data.get("status", ""),
            agency=data.get("agency", {}).get("name", "") if isinstance(data.get("agency"), dict) else str(data.get("agency", "")),
            agency_id=data.get("agency", {}).get("id", 0) if isinstance(data.get("agency"), dict) else 0,
            date_submitted=data.get("datetime_submitted"),
            date_due=data.get("date_due"),
            date_done=data.get("datetime_done"),
            tracking_id=data.get("tracking_id"),
            url=data.get("url", ""),
            absolute_url=data.get("absolute_url", ""),
        )


class MuckRockClient:
    """
    Client for the MuckRock FOIA filing platform API.

    Usage:
        client = MuckRockClient(MuckRockConfig(api_token="your_token"))

        # Search for agencies
        agencies = client.search_agencies("USDA")

        # File a request
        result = client.file_request(
            title="Inspection Records",
            agency_id=248,
            document_request="All inspection reports...",
        )

        # Check status
        foia = client.get_request(result["id"])
    """

    def __init__(self, config: MuckRockConfig) -> None:
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            headers={
                "Authorization": f"Token {config.api_token}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ---- Agency search ----

    def search_agencies(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Search for agencies on MuckRock.

        Args:
            query: Search term (agency name).
            jurisdiction: Filter by jurisdiction ID or slug.
            limit: Max results to return.

        Returns:
            List of agency dicts with 'id', 'name', 'jurisdiction', etc.
        """
        params: dict[str, Any] = {"search": query, "page_size": limit}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction

        resp = self._client.get("/agency/", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    def get_agency(self, agency_id: int) -> dict[str, Any]:
        """Get details for a specific agency by MuckRock ID."""
        resp = self._client.get(f"/agency/{agency_id}/")
        resp.raise_for_status()
        return resp.json()

    # ---- FOIA request filing ----

    def file_request(
        self,
        title: str,
        agency_id: int,
        document_request: str,
        full_text: Optional[str] = None,
        embargo: bool = False,
        permanent_embargo: bool = False,
    ) -> dict[str, Any]:
        """
        File a new FOIA request through MuckRock.

        Args:
            title: Short title for the request.
            agency_id: MuckRock agency ID (from search_agencies).
            document_request: The specific records being requested.
            full_text: Full request text (if different from document_request).
            embargo: Temporarily embargo the request from public view.
            permanent_embargo: Permanently embargo (requires pro account).

        Returns:
            Dict with 'id', 'url', and other request details.
        """
        payload = {
            "title": title,
            "agency": agency_id,
            "document_request": document_request,
        }
        if full_text:
            payload["full_text"] = full_text
        if embargo:
            payload["embargo"] = True
        if permanent_embargo:
            payload["permanent_embargo"] = True

        resp = self._client.post("/foia/", json=payload)
        resp.raise_for_status()
        return resp.json()

    def file_from_generated(
        self,
        generated: GeneratedRequest,
        title: Optional[str] = None,
        agency_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        File a request generated by our system through MuckRock.

        If agency_id is not provided, attempts to search for the agency.
        """
        if agency_id is None:
            agencies = self.search_agencies(generated.agency, limit=5)
            if not agencies:
                raise ValueError(
                    f"Could not find agency '{generated.agency}' on MuckRock. "
                    "Please provide the agency_id manually."
                )
            agency_id = agencies[0]["id"]

        request_title = title or f"{generated.context.topic} — {generated.agency}"
        if len(request_title) > 255:
            request_title = request_title[:252] + "..."

        return self.file_request(
            title=request_title,
            agency_id=agency_id,
            document_request=generated.text,
        )

    # ---- Request tracking ----

    def get_request(self, foia_id: int) -> MuckRockFOIA:
        """Get details for a specific FOIA request."""
        resp = self._client.get(f"/foia/{foia_id}/")
        resp.raise_for_status()
        return MuckRockFOIA.from_api(resp.json())

    def list_my_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[MuckRockFOIA]:
        """
        List the authenticated user's FOIA requests.

        Status options: 'submitted', 'ack', 'processed', 'appealing',
                       'fix', 'payment', 'rejected', 'no_docs', 'done',
                       'partial', 'abandoned'.
        """
        params: dict[str, Any] = {
            "user": self.config.username,
            "page": page,
            "page_size": page_size,
        }
        if status:
            params["status"] = status

        resp = self._client.get("/foia/", params=params)
        resp.raise_for_status()
        data = resp.json()
        return [MuckRockFOIA.from_api(r) for r in data.get("results", [])]

    def get_communications(self, foia_id: int) -> list[dict[str, Any]]:
        """Get all communications (messages) for a FOIA request."""
        resp = self._client.get(f"/foia/{foia_id}/communications/")
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    # ---- Jurisdiction search ----

    def search_jurisdictions(
        self,
        query: str,
        level: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Search for jurisdictions.

        Level options: 'f' (federal), 's' (state), 'l' (local).
        """
        params: dict[str, Any] = {"search": query, "page_size": limit}
        if level:
            params["level"] = level

        resp = self._client.get("/jurisdiction/", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

    # ---- Utility ----

    def check_auth(self) -> bool:
        """Verify that the API token is valid."""
        try:
            resp = self._client.get("/user/")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
