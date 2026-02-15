"""
Response parser — extract structured data from FOIA/RTI responses.

Parses agency response letters to extract:
- Determination (full grant, partial grant, denial)
- Exemptions cited
- Page counts (released, withheld, referred)
- Fee assessments
- Deadlines and appeal rights
- Assigned analyst information
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedResponse:
    """Structured data extracted from an agency response."""

    # Determination
    determination: str = "unknown"  # full_grant, partial_grant, denial, no_records, other
    determination_text: str = ""

    # Document counts
    pages_released: int = 0
    pages_withheld_full: int = 0
    pages_withheld_partial: int = 0
    pages_referred: int = 0
    documents_released: int = 0
    documents_withheld: int = 0

    # Exemptions
    exemptions: list[str] = field(default_factory=list)
    exemption_details: dict[str, str] = field(default_factory=dict)

    # Fees
    fee_charged: Optional[float] = None
    fee_waiver_granted: Optional[bool] = None

    # Processing
    assigned_analyst: str = ""
    tracking_number: str = ""
    response_date: str = ""

    # Appeal info
    appeal_deadline: str = ""
    appeal_address: str = ""

    # Raw
    raw_text: str = ""

    def summary(self) -> str:
        lines = [f"Determination: {self.determination}"]
        if self.pages_released:
            lines.append(f"Pages released: {self.pages_released}")
        if self.pages_withheld_full:
            lines.append(f"Pages withheld (full): {self.pages_withheld_full}")
        if self.pages_withheld_partial:
            lines.append(f"Pages withheld (partial): {self.pages_withheld_partial}")
        if self.exemptions:
            lines.append(f"Exemptions cited: {', '.join(self.exemptions)}")
        if self.fee_charged is not None:
            lines.append(f"Fee charged: ${self.fee_charged:.2f}")
        if self.tracking_number:
            lines.append(f"Tracking #: {self.tracking_number}")
        return "\n".join(lines)


# Known FOIA exemption patterns (US federal)
US_EXEMPTION_PATTERNS = {
    r"\(b\)\(1\)": "Exemption 1 — Classified national defense/foreign policy",
    r"\(b\)\(2\)": "Exemption 2 — Internal agency rules and practices",
    r"\(b\)\(3\)": "Exemption 3 — Specifically exempted by other statutes",
    r"\(b\)\(4\)": "Exemption 4 — Trade secrets and confidential commercial information",
    r"\(b\)\(5\)": "Exemption 5 — Inter-agency or intra-agency privileged communications",
    r"\(b\)\(6\)": "Exemption 6 — Personal privacy",
    r"\(b\)\(7\)\(A\)": "Exemption 7(A) — Law enforcement: could interfere with proceedings",
    r"\(b\)\(7\)\(B\)": "Exemption 7(B) — Law enforcement: deprive right to fair trial",
    r"\(b\)\(7\)\(C\)": "Exemption 7(C) — Law enforcement: personal privacy",
    r"\(b\)\(7\)\(D\)": "Exemption 7(D) — Law enforcement: confidential sources",
    r"\(b\)\(7\)\(E\)": "Exemption 7(E) — Law enforcement: techniques and procedures",
    r"\(b\)\(7\)\(F\)": "Exemption 7(F) — Law enforcement: endanger life/physical safety",
    r"\(b\)\(8\)": "Exemption 8 — Financial institution examination reports",
    r"\(b\)\(9\)": "Exemption 9 — Geological and geophysical well data",
}

# UK FOI exemption patterns
UK_EXEMPTION_PATTERNS = {
    r"[Ss]ection\s+21": "Section 21 — Information accessible by other means",
    r"[Ss]ection\s+22": "Section 22 — Information intended for future publication",
    r"[Ss]ection\s+23": "Section 23 — Security bodies",
    r"[Ss]ection\s+24": "Section 24 — National security",
    r"[Ss]ection\s+26": "Section 26 — Defence",
    r"[Ss]ection\s+27": "Section 27 — International relations",
    r"[Ss]ection\s+30": "Section 30 — Investigations and proceedings",
    r"[Ss]ection\s+31": "Section 31 — Law enforcement",
    r"[Ss]ection\s+35": "Section 35 — Formulation of government policy",
    r"[Ss]ection\s+36": "Section 36 — Prejudice to effective conduct of public affairs",
    r"[Ss]ection\s+38": "Section 38 — Health and safety",
    r"[Ss]ection\s+40": "Section 40 — Personal information",
    r"[Ss]ection\s+41": "Section 41 — Information provided in confidence",
    r"[Ss]ection\s+42": "Section 42 — Legal professional privilege",
    r"[Ss]ection\s+43": "Section 43 — Commercial interests",
    r"[Ss]ection\s+44": "Section 44 — Prohibitions on disclosure",
}

# India RTI exemption patterns
INDIA_EXEMPTION_PATTERNS = {
    r"[Ss]ection\s+8\(1\)\(a\)": "Section 8(1)(a) — Sovereignty, integrity, security of India",
    r"[Ss]ection\s+8\(1\)\(b\)": "Section 8(1)(b) — Expressly forbidden by court/tribunal",
    r"[Ss]ection\s+8\(1\)\(c\)": "Section 8(1)(c) — Breach of Parliamentary privilege",
    r"[Ss]ection\s+8\(1\)\(d\)": "Section 8(1)(d) — Commercial confidence, trade secrets",
    r"[Ss]ection\s+8\(1\)\(e\)": "Section 8(1)(e) — Fiduciary relationship",
    r"[Ss]ection\s+8\(1\)\(f\)": "Section 8(1)(f) — Received in confidence from foreign govt",
    r"[Ss]ection\s+8\(1\)\(g\)": "Section 8(1)(g) — Endanger life or physical safety",
    r"[Ss]ection\s+8\(1\)\(h\)": "Section 8(1)(h) — Impede investigation or prosecution",
    r"[Ss]ection\s+8\(1\)\(i\)": "Section 8(1)(i) — Cabinet papers",
    r"[Ss]ection\s+8\(1\)\(j\)": "Section 8(1)(j) — Personal information with no public interest",
}


class ResponseParser:
    """
    Parse agency response letters to extract structured data.

    Usage:
        parser = ResponseParser()
        parsed = parser.parse(response_text, jurisdiction="US-Federal")
        print(parsed.summary())
    """

    def parse(
        self,
        text: str,
        jurisdiction: str = "US-Federal",
    ) -> ParsedResponse:
        """Parse a response letter and extract structured data."""
        result = ParsedResponse(raw_text=text)

        result.determination = self._detect_determination(text)
        result.exemptions = self._extract_exemptions(text, jurisdiction)
        result.exemption_details = self._map_exemption_details(
            result.exemptions, jurisdiction
        )

        pages = self._extract_page_counts(text)
        result.pages_released = pages.get("released", 0)
        result.pages_withheld_full = pages.get("withheld_full", 0)
        result.pages_withheld_partial = pages.get("withheld_partial", 0)
        result.pages_referred = pages.get("referred", 0)

        result.tracking_number = self._extract_tracking_number(text)
        result.fee_charged = self._extract_fee(text)
        result.fee_waiver_granted = self._detect_fee_waiver(text)
        result.assigned_analyst = self._extract_analyst(text)

        return result

    # ---- Detection methods ----

    @staticmethod
    def _detect_determination(text: str) -> str:
        lower = text.lower()
        if any(phrase in lower for phrase in [
            "full grant", "granted in full", "fully granted",
            "releasing all", "all responsive records",
        ]):
            return "full_grant"
        if any(phrase in lower for phrase in [
            "partial grant", "granted in part", "partially granted",
            "releasing portions", "partial release",
            "withheld in part", "redacted",
        ]):
            return "partial_grant"
        if any(phrase in lower for phrase in [
            "denied", "denial", "we are unable to", "cannot release",
            "refusing your request", "exempt from disclosure",
        ]):
            return "denial"
        if any(phrase in lower for phrase in [
            "no responsive records", "no records responsive",
            "no documents were located", "no records located",
            "no records found",
        ]):
            return "no_records"
        return "unknown"

    @staticmethod
    def _extract_exemptions(text: str, jurisdiction: str) -> list[str]:
        exemptions: list[str] = []

        if jurisdiction in ("US-Federal",) or jurisdiction.startswith("US-State"):
            # Match (b)(1) through (b)(9) style citations
            pattern = r"\(b\)\(\d\)(?:\([A-F]\))?"
            matches = re.findall(pattern, text)
            exemptions.extend(sorted(set(matches)))

            # Also match "Exemption N" style
            ex_pattern = r"Exemption\s+(\d(?:\([A-F]\))?)"
            for m in re.findall(ex_pattern, text, re.IGNORECASE):
                formatted = f"(b)({m})"
                if formatted not in exemptions:
                    exemptions.append(formatted)

        elif jurisdiction == "UK":
            pattern = r"[Ss]ection\s+(\d{1,2})"
            matches = re.findall(pattern, text)
            exemptions.extend([f"Section {m}" for m in sorted(set(matches))])

        elif jurisdiction == "India":
            pattern = r"[Ss]ection\s+8\(1\)\(([a-j])\)"
            matches = re.findall(pattern, text)
            exemptions.extend([f"Section 8(1)({m})" for m in sorted(set(matches))])

        return exemptions

    @staticmethod
    def _map_exemption_details(
        exemptions: list[str], jurisdiction: str
    ) -> dict[str, str]:
        details: dict[str, str] = {}

        if jurisdiction in ("US-Federal",) or jurisdiction.startswith("US-State"):
            patterns = US_EXEMPTION_PATTERNS
        elif jurisdiction == "UK":
            patterns = UK_EXEMPTION_PATTERNS
        elif jurisdiction == "India":
            patterns = INDIA_EXEMPTION_PATTERNS
        else:
            return details

        for exemption in exemptions:
            for pattern, description in patterns.items():
                if re.search(pattern, exemption):
                    details[exemption] = description
                    break

        return details

    @staticmethod
    def _extract_page_counts(text: str) -> dict[str, int]:
        counts: dict[str, int] = {}

        # "X pages released" or "released X pages"
        released = re.findall(
            r"(\d{1,6})\s+pages?\s+(?:released|provided|enclosed|produced)"
            r"|(?:releas|provid|enclos|produc)\w+\s+(\d{1,6})\s+pages?",
            text, re.IGNORECASE,
        )
        for groups in released:
            for g in groups:
                if g:
                    counts["released"] = counts.get("released", 0) + int(g)

        # "X pages withheld"
        withheld = re.findall(
            r"(\d{1,6})\s+pages?\s+(?:withheld|redacted|denied)"
            r"|(?:withheld|redacted|denied)\s+(\d{1,6})\s+pages?",
            text, re.IGNORECASE,
        )
        for groups in withheld:
            for g in groups:
                if g:
                    counts["withheld_full"] = counts.get("withheld_full", 0) + int(g)

        # "X pages referred"
        referred = re.findall(
            r"(\d{1,6})\s+pages?\s+referred"
            r"|referred\s+(\d{1,6})\s+pages?",
            text, re.IGNORECASE,
        )
        for groups in referred:
            for g in groups:
                if g:
                    counts["referred"] = counts.get("referred", 0) + int(g)

        return counts

    @staticmethod
    def _extract_tracking_number(text: str) -> str:
        # Common formats: FOIA-2026-00123, F-2026-000456, 2026-FOIA-00789
        patterns = [
            r"(?:FOIA|FOI|RTI|ATI)[-\s]?\d{4}[-\s]?\d{3,8}",
            r"\d{4}[-\s](?:FOIA|FOI)[-\s]?\d{3,8}",
            r"(?:Case|Reference|Tracking|Request)\s*(?:No\.?|Number|#|ID)[:\s]*([A-Z0-9\-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return ""

    @staticmethod
    def _extract_fee(text: str) -> Optional[float]:
        patterns = [
            r"\$\s*(\d{1,6}(?:\.\d{2})?)",
            r"(?:fee|charge|cost)\s*(?:of|:)\s*\$?\s*(\d{1,6}(?:\.\d{2})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _detect_fee_waiver(text: str) -> Optional[bool]:
        lower = text.lower()
        if "fee waiver" in lower and any(
            w in lower for w in ["granted", "approved", "waived"]
        ):
            return True
        if "fee waiver" in lower and any(
            w in lower for w in ["denied", "rejected", "not granted"]
        ):
            return False
        return None

    @staticmethod
    def _extract_analyst(text: str) -> str:
        patterns = [
            r"(?:analyst|specialist|officer|processor)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"(?:contact|questions).*?([A-Z][a-z]+\s+[A-Z][a-z]+)\s+at",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""
