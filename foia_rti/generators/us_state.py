"""
US State public records request generator.

Each state has its own public records law with unique statutory citations,
response timelines, and fee structures. This module covers at least the
ten largest animal agriculture states by livestock inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from foia_rti.generators.generator_base import (
    GeneratedRequest,
    RequestContext,
    RequestGenerator,
)


@dataclass
class StateInfo:
    """Legal and procedural details for a single state's public records law."""

    state: str
    abbreviation: str
    statute_name: str
    statute_citation: str
    response_days: int
    response_type: str  # "calendar" or "business"
    fee_notes: str
    appeal_body: str
    key_agencies: dict[str, dict[str, str]]
    notes: str = ""


# ---------------------------------------------------------------------------
# State registry — real statutes for major animal-agriculture states
# ---------------------------------------------------------------------------

STATE_REGISTRY: dict[str, StateInfo] = {
    "IA": StateInfo(
        state="Iowa",
        abbreviation="IA",
        statute_name="Iowa Open Records Law",
        statute_citation="Iowa Code Chapter 22",
        response_days=20,
        response_type="calendar",
        fee_notes=(
            "Agencies may charge reasonable fees for examination and copying. "
            "Iowa Code § 22.3(2). Costs must be itemized."
        ),
        appeal_body="Iowa Public Information Board (IPIB)",
        key_agencies={
            "Iowa DNR": {
                "full_name": "Iowa Department of Natural Resources",
                "address": "502 East 9th Street, Des Moines, IA 50319",
                "email": "webmaster@dnr.iowa.gov",
                "notes": "CAFO permits, manure management plans, AFO inspections.",
            },
            "Iowa Dept of Agriculture": {
                "full_name": "Iowa Department of Agriculture and Land Stewardship",
                "address": "Wallace State Office Building, 502 E 9th St, Des Moines, IA 50319",
                "email": "iowaagriculture@iowaagriculture.gov",
                "notes": "Livestock facility permits, disease reports.",
            },
        },
    ),
    "NC": StateInfo(
        state="North Carolina",
        abbreviation="NC",
        statute_name="North Carolina Public Records Law",
        statute_citation="N.C. Gen. Stat. Chapter 132",
        response_days=0,
        response_type="calendar",
        fee_notes=(
            "Agencies must respond 'as promptly as possible.' No specific day "
            "limit, but unreasonable delay is actionable. Fees limited to actual "
            "cost of reproduction. N.C.G.S. § 132-6.2."
        ),
        appeal_body="Superior Court (no administrative appeal body)",
        key_agencies={
            "NC DEQ": {
                "full_name": "North Carolina Department of Environmental Quality",
                "address": "217 West Jones Street, Raleigh, NC 27603",
                "email": "publicrecords@ncdenr.gov",
                "notes": "Swine waste permits, lagoon compliance, water quality data.",
            },
        },
        notes=(
            "North Carolina has no fixed response deadline; statute says "
            "'as promptly as possible.' Consider citing case law: "
            "News & Observer Publ'g Co. v. Poole, 330 N.C. 465 (1992)."
        ),
    ),
    "AR": StateInfo(
        state="Arkansas",
        abbreviation="AR",
        statute_name="Arkansas Freedom of Information Act",
        statute_citation="Ark. Code Ann. § 25-19-101 et seq. (FOIA Act 541 of 1967)",
        response_days=3,
        response_type="business",
        fee_notes=(
            "May charge only actual costs. Ark. Code § 25-19-105(d). "
            "Cannot charge for time spent reviewing records for exemptions."
        ),
        appeal_body="Circuit Court",
        key_agencies={
            "ADEQ": {
                "full_name": "Arkansas Department of Energy and Environment — "
                             "Division of Environmental Quality",
                "address": "5301 Northshore Drive, North Little Rock, AR 72118",
                "email": "FOIA@adeq.state.ar.us",
                "notes": "Poultry CAFO permits, Buffalo River watershed data.",
            },
        },
    ),
    "TX": StateInfo(
        state="Texas",
        abbreviation="TX",
        statute_name="Texas Public Information Act",
        statute_citation="Tex. Gov't Code Chapter 552",
        response_days=10,
        response_type="business",
        fee_notes=(
            "Agencies must provide cost estimate before fulfilling request if "
            "charges exceed $40. Tex. Gov't Code § 552.2615. Labor charges "
            "capped at $15/hour for programming."
        ),
        appeal_body="Texas Attorney General, Open Records Division",
        key_agencies={
            "TCEQ": {
                "full_name": "Texas Commission on Environmental Quality",
                "address": "P.O. Box 13087, Austin, TX 78711-3087",
                "email": "piamail@tceq.texas.gov",
                "notes": "CAFO permits, water discharge violations, air quality.",
            },
            "TAHC": {
                "full_name": "Texas Animal Health Commission",
                "address": "P.O. Box 12966, Austin, TX 78711",
                "email": "comments@tahc.texas.gov",
                "notes": "Disease reports, quarantine orders, livestock movement.",
            },
        },
    ),
    "CA": StateInfo(
        state="California",
        abbreviation="CA",
        statute_name="California Public Records Act",
        statute_citation="Cal. Gov't Code § 7920.000 et seq. (formerly § 6250 et seq.)",
        response_days=10,
        response_type="calendar",
        fee_notes=(
            "Only direct costs of duplication. No charges for search or "
            "review time. Cal. Gov't Code § 7922.530."
        ),
        appeal_body="Superior Court (also may petition the State Auditor for fee disputes)",
        key_agencies={
            "CDFA": {
                "full_name": "California Department of Food and Agriculture",
                "address": "1220 N Street, Sacramento, CA 95814",
                "email": "PRA.Coordinator@cdfa.ca.gov",
                "notes": "Dairy permits, livestock inspection, feed lot operations.",
            },
            "CARB": {
                "full_name": "California Air Resources Board",
                "address": "P.O. Box 2815, Sacramento, CA 95812",
                "email": "helpline@arb.ca.gov",
                "notes": "Methane emissions from dairy and livestock.",
            },
        },
    ),
    "MN": StateInfo(
        state="Minnesota",
        abbreviation="MN",
        statute_name="Minnesota Government Data Practices Act",
        statute_citation="Minn. Stat. Chapter 13",
        response_days=0,
        response_type="business",
        fee_notes=(
            "Agencies must respond 'immediately if data is available' or provide "
            "a timeline. Fees limited to actual costs of searching and copying. "
            "Minn. Stat. § 13.03, subd. 3."
        ),
        appeal_body="Commissioner of the Department of Administration, or District Court",
        key_agencies={
            "MPCA": {
                "full_name": "Minnesota Pollution Control Agency",
                "address": "520 Lafayette Rd N, St. Paul, MN 55155",
                "email": "data.practices@state.mn.us",
                "notes": "Feedlot permits, water quality, CAFO compliance.",
            },
        },
        notes="Minnesota classifies data rather than records — frame requests around 'government data.'",
    ),
    "NE": StateInfo(
        state="Nebraska",
        abbreviation="NE",
        statute_name="Nebraska Public Records Statutes",
        statute_citation="Neb. Rev. Stat. §§ 84-712 to 84-712.09",
        response_days=4,
        response_type="business",
        fee_notes=(
            "Reasonable fees for copies; actual costs only. "
            "Neb. Rev. Stat. § 84-712(3)."
        ),
        appeal_body="District Court",
        key_agencies={
            "NDEQ": {
                "full_name": "Nebraska Department of Environment and Energy",
                "address": "245 Fallbrook Blvd, Suite 202, Lincoln, NE 68521",
                "email": "dee.publicrecords@nebraska.gov",
                "notes": "Livestock waste permits, water quality monitoring.",
            },
        },
    ),
    "KS": StateInfo(
        state="Kansas",
        abbreviation="KS",
        statute_name="Kansas Open Records Act",
        statute_citation="K.S.A. § 45-215 et seq.",
        response_days=3,
        response_type="business",
        fee_notes=(
            "Agencies may charge reasonable fees not to exceed actual cost. "
            "K.S.A. § 45-219."
        ),
        appeal_body="District Court (may also contact the Kansas Attorney General for opinion)",
        key_agencies={
            "KDHE": {
                "full_name": "Kansas Department of Health and Environment",
                "address": "1000 SW Jackson St, Suite 540, Topeka, KS 66612",
                "email": "kdheinfo@ks.gov",
                "notes": "CAFO permits, water pollution from feedlots.",
            },
        },
    ),
    "WI": StateInfo(
        state="Wisconsin",
        abbreviation="WI",
        statute_name="Wisconsin Public Records Law",
        statute_citation="Wis. Stat. §§ 19.31–19.39",
        response_days=0,
        response_type="calendar",
        fee_notes=(
            "Agencies must respond 'as soon as practicable and without delay.' "
            "Fees limited to actual, necessary, and direct costs. "
            "Wis. Stat. § 19.35(3)."
        ),
        appeal_body="Circuit Court; may also seek a mandamus action",
        key_agencies={
            "WDNR": {
                "full_name": "Wisconsin Department of Natural Resources",
                "address": "101 S Webster St, Madison, WI 53707",
                "email": "DNROpenRecords@wisconsin.gov",
                "notes": "CAFO permits, manure spreading compliance, water quality.",
            },
            "DATCP": {
                "full_name": "Wisconsin Department of Agriculture, Trade and Consumer Protection",
                "address": "2811 Agriculture Dr, Madison, WI 53708",
                "email": "datcpweb@wisconsin.gov",
                "notes": "Dairy plant inspections, livestock facility siting.",
            },
        },
    ),
    "GA": StateInfo(
        state="Georgia",
        abbreviation="GA",
        statute_name="Georgia Open Records Act",
        statute_citation="O.C.G.A. § 50-18-70 et seq.",
        response_days=3,
        response_type="business",
        fee_notes=(
            "Fees capped at 25 cents per page for letter/legal copies. "
            "O.C.G.A. § 50-18-71(c). Search/retrieval fees cannot exceed "
            "the lowest-paid full-time employee's hourly rate."
        ),
        appeal_body="Superior Court; AG may mediate disputes",
        key_agencies={
            "GA EPD": {
                "full_name": "Georgia Environmental Protection Division",
                "address": "2 Martin Luther King Jr. Dr. SE, Suite 1456, Atlanta, GA 30334",
                "email": "epd.openrecords@dnr.ga.gov",
                "notes": "Poultry operation permits, water discharge, air quality.",
            },
        },
    ),
    "IN": StateInfo(
        state="Indiana",
        abbreviation="IN",
        statute_name="Indiana Access to Public Records Act",
        statute_citation="Ind. Code § 5-14-3",
        response_days=7,
        response_type="calendar",
        fee_notes=(
            "Copies at actual cost. May not charge for first two hours of "
            "staff time. IC § 5-14-3-8."
        ),
        appeal_body="Public Access Counselor (informal opinion); then court",
        key_agencies={
            "IDEM": {
                "full_name": "Indiana Department of Environmental Management",
                "address": "100 N. Senate Ave., Indianapolis, IN 46204",
                "email": "publicrecords@idem.in.gov",
                "notes": "CFO permits, livestock waste management records.",
            },
        },
    ),
    "PA": StateInfo(
        state="Pennsylvania",
        abbreviation="PA",
        statute_name="Pennsylvania Right-to-Know Law",
        statute_citation="65 P.S. § 67.101 et seq.",
        response_days=5,
        response_type="business",
        fee_notes=(
            "Fees set by the Office of Open Records. Duplication fees "
            "capped at 25 cents per page. 65 P.S. § 67.1307."
        ),
        appeal_body="Office of Open Records (OOR) within 15 business days",
        key_agencies={
            "PA DEP": {
                "full_name": "Pennsylvania Department of Environmental Protection",
                "address": "Rachel Carson State Office Building, 400 Market St, Harrisburg, PA 17101",
                "email": "RA-EPRTK@pa.gov",
                "notes": "CAFO permits, nutrient management plans, water quality.",
            },
        },
    ),
}


# ---------------------------------------------------------------------------
# Jinja2 template for state-level requests
# ---------------------------------------------------------------------------

STATE_REQUEST_TEMPLATE = """\
{{ filing_date }}

{% if agency_address %}
{{ agency_full_name }}
{{ agency_address }}
{% endif %}

{% if agency_email %}Via email: {{ agency_email }}{% endif %}

Re: Public Records Request under {{ statute_name }}

Dear Records Custodian:

Pursuant to the {{ statute_name }}, {{ statute_citation }}, I request access \
to and copies of the following public records:

{% for record in specific_records %}
{{ loop.index }}. {{ record }}
{% endfor %}

{% if keywords %}
Specifically, I request records containing or relating to the following \
terms: {{ keywords | join(', ') }}.
{% endif %}

{% if facilities %}
This request pertains to the following facilities or entities: \
{{ facilities | join('; ') }}.
{% endif %}

DATE RANGE: {{ date_range }}.

FORMAT: I request that responsive records be provided in {{ preferred_format }} \
format.

{% if fee_waiver %}
FEE WAIVER REQUEST:

I request a waiver or reduction of fees associated with this request. The \
information sought is in the public interest and will contribute to the \
public's understanding of government operations. {{ requester_org }} is a \
nonprofit organization and the records will be used for educational and \
public interest purposes, not for commercial use.
{% endif %}

{% if response_days > 0 %}
Under {{ statute_citation }}, I expect a response within {{ response_days }} \
{{ response_type }} days of your receipt of this request. If any records are \
withheld, please identify them and cite the specific statutory exemption \
authorizing the withholding.
{% else %}
The {{ statute_name }} requires agencies to respond as promptly as possible. \
I request your timely compliance. If any records are withheld, please identify \
them and cite the specific statutory exemption authorizing the withholding.
{% endif %}

{% if state_notes %}
NOTE: {{ state_notes }}
{% endif %}

{% if additional_notes %}
ADDITIONAL INFORMATION: {{ additional_notes }}
{% endif %}

Thank you for your prompt attention to this request. Please contact me with \
any questions.

Sincerely,

{{ requester_name }}
{% if requester_org %}{{ requester_org }}{% endif %}
{% if requester_address %}{{ requester_address }}{% endif %}
{% if requester_email %}{{ requester_email }}{% endif %}
{% if requester_phone %}{{ requester_phone }}{% endif %}
"""


class USStateGenerator(RequestGenerator):
    """Generate public records requests for US state agencies."""

    def __init__(self) -> None:
        super().__init__()

    def generate(self, context: RequestContext) -> GeneratedRequest:
        state_abbr = self._resolve_state(context.jurisdiction)
        state_info = STATE_REGISTRY.get(state_abbr)
        if state_info is None:
            raise ValueError(
                f"Unknown state '{context.jurisdiction}'. Supported states: "
                f"{', '.join(STATE_REGISTRY.keys())}"
            )

        agency_data = self._resolve_agency(context.agency, state_info)

        text = self._render(
            STATE_REQUEST_TEMPLATE,
            context,
            statute_name=state_info.statute_name,
            statute_citation=state_info.statute_citation,
            response_days=state_info.response_days,
            response_type=state_info.response_type,
            agency_full_name=agency_data.get("full_name", context.agency),
            agency_address=agency_data.get("address", ""),
            agency_email=agency_data.get("email", ""),
            state_notes=state_info.notes,
            fee_waiver=context.fee_waiver,
        )

        return GeneratedRequest(
            text=text.strip(),
            jurisdiction=f"US-State-{state_abbr}",
            agency=agency_data.get("full_name", context.agency),
            legal_basis=f"{state_info.statute_name}, {state_info.statute_citation}",
            estimated_deadline_days=state_info.response_days or 10,
            filing_method="email",
            fee_notes=state_info.fee_notes,
            context=context,
            metadata={
                "state": state_abbr,
                "appeal_body": state_info.appeal_body,
                "agency_email": agency_data.get("email", ""),
            },
        )

    def get_agencies(self) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for abbr, info in STATE_REGISTRY.items():
            for name, details in info.key_agencies.items():
                result[f"{abbr} — {name}"] = details
        return result

    def get_legal_basis(self) -> str:
        lines = []
        for abbr, info in sorted(STATE_REGISTRY.items()):
            lines.append(f"  {info.state} ({abbr}): {info.statute_name}, {info.statute_citation}")
        return "State public records laws:\n" + "\n".join(lines)

    def get_fee_waiver_language(self, context: RequestContext) -> str:
        return (
            "I request a waiver or reduction of fees. The information is sought "
            "in the public interest for educational and nonprofit purposes."
        )

    def get_appeal_info(self) -> dict[str, str]:
        lines = []
        for abbr, info in sorted(STATE_REGISTRY.items()):
            lines.append(f"  {info.state}: {info.appeal_body}")
        return {
            "overview": "Appeals vary by state. Most allow either administrative appeal or direct court action.",
            "by_state": "\n".join(lines),
        }

    def get_supported_states(self) -> list[str]:
        return sorted(STATE_REGISTRY.keys())

    # ---- internals ----

    @staticmethod
    def _resolve_state(raw: str) -> str:
        """Normalize state input to two-letter abbreviation."""
        upper = raw.upper().strip().replace("US-STATE-", "")
        if upper in STATE_REGISTRY:
            return upper
        # Try full name match
        for abbr, info in STATE_REGISTRY.items():
            if info.state.upper() == upper:
                return abbr
        return upper

    @staticmethod
    def _resolve_agency(raw: str, state_info: StateInfo) -> dict[str, str]:
        upper = raw.upper().strip()
        for name, details in state_info.key_agencies.items():
            if upper in name.upper() or name.upper() in upper:
                return details
        # Return what we have even if no exact match
        if state_info.key_agencies:
            first_key = next(iter(state_info.key_agencies))
            return state_info.key_agencies[first_key]
        return {"full_name": raw}
