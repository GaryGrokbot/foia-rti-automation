"""
Redaction and exemption abuse detector.

Flags suspicious patterns in FOIA/RTI responses that may indicate
improper withholding, over-redaction, or abuse of exemptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from foia_rti.analysis.response_parser import ParsedResponse


@dataclass
class RedactionFlag:
    """A single suspicious finding in a FOIA response."""

    severity: str  # "high", "medium", "low"
    category: str
    description: str
    recommendation: str
    exemption: Optional[str] = None


@dataclass
class RedactionReport:
    """Complete analysis of redaction patterns in a response."""

    flags: list[RedactionFlag] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0 to 1.0
    summary: str = ""
    appeal_recommended: bool = False

    def add_flag(self, flag: RedactionFlag) -> None:
        self.flags.append(flag)
        self._recalculate_score()

    def _recalculate_score(self) -> None:
        if not self.flags:
            self.risk_score = 0.0
            return
        weights = {"high": 0.4, "medium": 0.2, "low": 0.1}
        total = sum(weights.get(f.severity, 0.1) for f in self.flags)
        self.risk_score = min(1.0, total)
        self.appeal_recommended = self.risk_score >= 0.3

    def format_report(self) -> str:
        lines = [
            f"REDACTION ANALYSIS REPORT",
            f"Risk Score: {self.risk_score:.1%}",
            f"Appeal Recommended: {'Yes' if self.appeal_recommended else 'No'}",
            f"Flags Found: {len(self.flags)}",
            "",
        ]
        for i, flag in enumerate(self.flags, 1):
            lines.append(f"--- Flag {i} [{flag.severity.upper()}] ---")
            lines.append(f"Category: {flag.category}")
            lines.append(f"Issue: {flag.description}")
            if flag.exemption:
                lines.append(f"Exemption: {flag.exemption}")
            lines.append(f"Recommendation: {flag.recommendation}")
            lines.append("")

        if self.appeal_recommended:
            lines.append(
                "RECOMMENDATION: Based on the patterns detected, an appeal "
                "is recommended. The withholdings show indicators of potential "
                "over-redaction or improper exemption usage."
            )
        return "\n".join(lines)


# Exemption-specific rules for US FOIA
US_EXEMPTION_RULES = {
    "(b)(4)": {
        "name": "Trade Secrets / Confidential Commercial Information",
        "abuse_indicators": [
            "Agency did not consult with submitter (required for reverse FOIA)",
            "Information is already publicly available",
            "Information does not reveal competitive advantage",
            "Government-generated analyses or summaries should be segregable",
        ],
        "key_cases": [
            "Food Marketing Institute v. Argus Leader Media, 588 U.S. 427 (2019)",
            "National Parks & Conservation Ass'n v. Morton, 498 F.2d 765 (D.C. Cir. 1974)",
        ],
    },
    "(b)(5)": {
        "name": "Deliberative Process Privilege",
        "abuse_indicators": [
            "Document is factual rather than deliberative",
            "Decision has already been made (privilege may not apply post-decision)",
            "Statistical data or factual summaries should be segregable",
            "Agency did not demonstrate the document is both predecisional and deliberative",
        ],
        "key_cases": [
            "NLRB v. Sears, Roebuck & Co., 421 U.S. 132 (1975)",
            "EPA v. Mink, 410 U.S. 73 (1973)",
        ],
    },
    "(b)(6)": {
        "name": "Personal Privacy",
        "abuse_indicators": [
            "Names of government officials acting in official capacity should not be withheld",
            "Information about corporate entities (not individuals) improperly withheld",
            "Blanket withholding without balancing public interest vs. privacy",
        ],
        "key_cases": [
            "Department of the Air Force v. Rose, 425 U.S. 352 (1976)",
            "U.S. Dept. of Justice v. Reporters Committee, 489 U.S. 749 (1989)",
        ],
    },
    "(b)(7)(C)": {
        "name": "Law Enforcement — Personal Privacy",
        "abuse_indicators": [
            "Applied to inspection records that are not law enforcement records",
            "USDA inspection reports are generally not 'law enforcement' records",
            "No nexus to law enforcement purpose demonstrated",
        ],
        "key_cases": [
            "Tax Analysts v. IRS, 294 F.3d 71 (D.C. Cir. 2002)",
        ],
    },
    "(b)(7)(E)": {
        "name": "Law Enforcement Techniques",
        "abuse_indicators": [
            "Technique is already publicly known or commonly used",
            "Applied to routine inspection procedures",
            "No demonstration that disclosure would risk circumvention",
        ],
        "key_cases": [
            "Blackwell v. FBI, 646 F.3d 37 (D.C. Cir. 2011)",
        ],
    },
}


class RedactionDetector:
    """
    Analyze FOIA/RTI responses for suspicious redaction patterns.

    Usage:
        detector = RedactionDetector()
        parsed = ResponseParser().parse(response_text, "US-Federal")
        report = detector.analyze(parsed, "US-Federal")
        print(report.format_report())
    """

    def analyze(
        self,
        parsed: ParsedResponse,
        jurisdiction: str = "US-Federal",
    ) -> RedactionReport:
        """Run all detection rules and produce a report."""
        report = RedactionReport()

        if jurisdiction in ("US-Federal",) or jurisdiction.startswith("US-State"):
            self._check_excessive_withholding(parsed, report)
            self._check_exemption_patterns_us(parsed, report)
            self._check_blanket_denial(parsed, report)
            self._check_segregability(parsed, report)
            self._check_b4_overuse(parsed, report)
            self._check_b5_overuse(parsed, report)
            self._check_b7_misapplication(parsed, report)
            self._check_no_vaughn_index(parsed, report)
        elif jurisdiction == "UK":
            self._check_excessive_withholding(parsed, report)
            self._check_uk_patterns(parsed, report)
        elif jurisdiction == "India":
            self._check_excessive_withholding(parsed, report)
            self._check_india_patterns(parsed, report)

        report.summary = self._generate_summary(report)
        return report

    # ---- US Federal checks ----

    @staticmethod
    def _check_excessive_withholding(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        total = parsed.pages_released + parsed.pages_withheld_full
        if total == 0:
            return
        withhold_ratio = parsed.pages_withheld_full / total
        if withhold_ratio > 0.8:
            report.add_flag(
                RedactionFlag(
                    severity="high",
                    category="Excessive Withholding",
                    description=(
                        f"{parsed.pages_withheld_full} of {total} pages "
                        f"({withhold_ratio:.0%}) were withheld in full. "
                        "This ratio is unusually high and may indicate "
                        "over-classification or blanket withholding."
                    ),
                    recommendation=(
                        "Appeal the withholding. Request a Vaughn index "
                        "detailing the justification for each withheld document."
                    ),
                )
            )
        elif withhold_ratio > 0.5:
            report.add_flag(
                RedactionFlag(
                    severity="medium",
                    category="High Withholding Rate",
                    description=(
                        f"{withhold_ratio:.0%} of pages withheld. "
                        "Review exemption justifications carefully."
                    ),
                    recommendation=(
                        "Request more detailed justification for each "
                        "category of withheld records."
                    ),
                )
            )

    @staticmethod
    def _check_exemption_patterns_us(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        if len(parsed.exemptions) >= 4:
            report.add_flag(
                RedactionFlag(
                    severity="medium",
                    category="Multiple Exemptions",
                    description=(
                        f"{len(parsed.exemptions)} different exemptions cited. "
                        "Using many exemptions for a single request may indicate "
                        "a 'kitchen sink' approach to withholding."
                    ),
                    recommendation=(
                        "Challenge each exemption individually. Agencies must "
                        "justify each exemption for each specific withholding."
                    ),
                )
            )

    @staticmethod
    def _check_blanket_denial(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        if parsed.determination == "denial" and parsed.pages_released == 0:
            report.add_flag(
                RedactionFlag(
                    severity="high",
                    category="Blanket Denial",
                    description=(
                        "The entire request was denied with no records released. "
                        "Total denials warrant close scrutiny."
                    ),
                    recommendation=(
                        "File an appeal. Under 5 U.S.C. Section 552(b), the "
                        "agency must demonstrate that an exemption applies to "
                        "each withheld record. A blanket denial without "
                        "document-by-document review is improper."
                    ),
                )
            )

    @staticmethod
    def _check_segregability(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        if parsed.pages_withheld_full > 0 and parsed.pages_withheld_partial == 0:
            report.add_flag(
                RedactionFlag(
                    severity="medium",
                    category="No Partial Releases",
                    description=(
                        "All withheld pages were withheld in full with no "
                        "partial redactions. Under FOIA, agencies must release "
                        "all reasonably segregable non-exempt portions."
                    ),
                    recommendation=(
                        "Challenge on segregability grounds. Cite 5 U.S.C. "
                        "Section 552(b) (final sentence): 'Any reasonably "
                        "segregable portion of a record shall be provided.'"
                    ),
                )
            )

    @staticmethod
    def _check_b4_overuse(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        b4_exemptions = [e for e in parsed.exemptions if "(b)(4)" in e or "(4)" in e]
        if b4_exemptions:
            report.add_flag(
                RedactionFlag(
                    severity="low",
                    category="Exemption 4 — Trade Secrets",
                    description=(
                        "Exemption (b)(4) was cited. In the context of animal "
                        "agriculture, this exemption is sometimes improperly "
                        "applied to shield routine operational data."
                    ),
                    recommendation=(
                        "Verify whether the submitter was given notice under "
                        "Executive Order 12600. Challenge if the information "
                        "was submitted to the government voluntarily or is "
                        "already publicly available."
                    ),
                    exemption="(b)(4)",
                )
            )

    @staticmethod
    def _check_b5_overuse(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        b5_exemptions = [e for e in parsed.exemptions if "(b)(5)" in e or "(5)" in e]
        if b5_exemptions:
            report.add_flag(
                RedactionFlag(
                    severity="medium",
                    category="Exemption 5 — Deliberative Process",
                    description=(
                        "Exemption (b)(5) is the most abused FOIA exemption. "
                        "It requires the document be both predecisional AND "
                        "deliberative. Factual material embedded in deliberative "
                        "documents must be segregated and released."
                    ),
                    recommendation=(
                        "Challenge by arguing: (1) the document contains "
                        "segregable factual material; (2) the decision has been "
                        "made, so the privilege no longer protects; or (3) the "
                        "document is not truly deliberative. Cite NLRB v. Sears."
                    ),
                    exemption="(b)(5)",
                )
            )

    @staticmethod
    def _check_b7_misapplication(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        b7 = [e for e in parsed.exemptions if "(b)(7)" in e or "(7)" in e]
        if b7:
            report.add_flag(
                RedactionFlag(
                    severity="medium",
                    category="Exemption 7 — Law Enforcement",
                    description=(
                        "Exemption (b)(7) requires a law enforcement nexus. "
                        "Routine inspection records (e.g., USDA-APHIS Animal "
                        "Welfare Act inspections, FSIS slaughter inspections) "
                        "may not qualify as 'law enforcement' records under "
                        "this exemption."
                    ),
                    recommendation=(
                        "Challenge the law enforcement nexus. Argue that "
                        "regulatory inspections for compliance purposes are "
                        "not compiled for 'law enforcement purposes' within "
                        "the meaning of Exemption 7."
                    ),
                    exemption="(b)(7)",
                )
            )

    @staticmethod
    def _check_no_vaughn_index(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        if (
            parsed.pages_withheld_full > 10
            and parsed.determination in ("denial", "partial_grant")
            and "vaughn" not in parsed.raw_text.lower()
        ):
            report.add_flag(
                RedactionFlag(
                    severity="low",
                    category="No Vaughn Index",
                    description=(
                        "The response withheld substantial records without "
                        "providing a Vaughn index. While not required at the "
                        "administrative stage, requesting one can reveal "
                        "improper withholding patterns."
                    ),
                    recommendation=(
                        "In your appeal, request a Vaughn index that identifies "
                        "each withheld document and the specific exemption(s) "
                        "applied. See Vaughn v. Rosen, 484 F.2d 820 (D.C. Cir. 1973)."
                    ),
                )
            )

    # ---- UK checks ----

    @staticmethod
    def _check_uk_patterns(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        for exemption in parsed.exemptions:
            if "43" in exemption:
                report.add_flag(
                    RedactionFlag(
                        severity="medium",
                        category="Section 43 — Commercial Interests",
                        description=(
                            "Section 43 is a qualified exemption and requires "
                            "a public interest test. The authority must demonstrate "
                            "that the public interest in maintaining the exemption "
                            "outweighs the public interest in disclosure."
                        ),
                        recommendation=(
                            "Request internal review. Argue that the public "
                            "interest in transparency about animal agriculture "
                            "practices outweighs commercial sensitivity."
                        ),
                        exemption=exemption,
                    )
                )
            if "35" in exemption or "36" in exemption:
                report.add_flag(
                    RedactionFlag(
                        severity="medium",
                        category="Policy Formulation Exemption",
                        description=(
                            "Sections 35/36 are qualified exemptions frequently "
                            "used to shield policy development. Challenge if the "
                            "policy decision has already been taken."
                        ),
                        recommendation=(
                            "Argue that once a policy decision is made, the "
                            "public interest shifts decisively toward disclosure."
                        ),
                        exemption=exemption,
                    )
                )

    # ---- India checks ----

    @staticmethod
    def _check_india_patterns(
        parsed: ParsedResponse, report: RedactionReport
    ) -> None:
        for exemption in parsed.exemptions:
            if "8(1)(d)" in exemption:
                report.add_flag(
                    RedactionFlag(
                        severity="medium",
                        category="Section 8(1)(d) — Commercial Confidence",
                        description=(
                            "Section 8(1)(d) protects commercial confidence and "
                            "trade secrets. However, Section 8(2) provides that "
                            "information may still be disclosed if the public "
                            "interest outweighs the harm."
                        ),
                        recommendation=(
                            "Appeal citing Section 8(2). Argue that public interest "
                            "in food safety, animal welfare, and environmental "
                            "protection outweighs commercial confidence."
                        ),
                        exemption=exemption,
                    )
                )
            if "8(1)(j)" in exemption:
                report.add_flag(
                    RedactionFlag(
                        severity="low",
                        category="Section 8(1)(j) — Personal Information",
                        description=(
                            "Section 8(1)(j) exempts personal information with "
                            "no relationship to public activity. However, "
                            "information about public officials acting in "
                            "their official capacity is not exempt."
                        ),
                        recommendation=(
                            "Challenge if the withheld information relates to "
                            "official duties of public servants, particularly "
                            "inspectors and regulatory officers."
                        ),
                        exemption=exemption,
                    )
                )

    @staticmethod
    def _generate_summary(report: RedactionReport) -> str:
        if not report.flags:
            return "No suspicious patterns detected in the agency response."
        high = sum(1 for f in report.flags if f.severity == "high")
        med = sum(1 for f in report.flags if f.severity == "medium")
        low = sum(1 for f in report.flags if f.severity == "low")
        parts = []
        if high:
            parts.append(f"{high} high-severity")
        if med:
            parts.append(f"{med} medium-severity")
        if low:
            parts.append(f"{low} low-severity")
        return (
            f"Detected {', '.join(parts)} issue(s). "
            f"Overall risk score: {report.risk_score:.0%}. "
            f"{'Appeal recommended.' if report.appeal_recommended else 'Monitor closely.'}"
        )
