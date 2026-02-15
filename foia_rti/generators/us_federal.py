"""
US Federal FOIA request generator.

Generates requests under the Freedom of Information Act, 5 U.S.C. Section 552,
targeting federal agencies with jurisdiction over animal agriculture:
USDA, EPA, FDA, OSHA, and others.
"""

from __future__ import annotations

from typing import Any, Optional

from foia_rti.generators.generator_base import (
    GeneratedRequest,
    RequestContext,
    RequestGenerator,
)


# ---------------------------------------------------------------------------
# Agency registry — real FOIA contacts and submission info
# ---------------------------------------------------------------------------

US_FEDERAL_AGENCIES: dict[str, dict[str, str]] = {
    "USDA-APHIS": {
        "full_name": "United States Department of Agriculture — "
                     "Animal and Plant Health Inspection Service",
        "foia_officer": "FOIA Officer, Legislative and Public Affairs",
        "address": "4700 River Road, Unit 50, Riverdale, MD 20737-1232",
        "email": "APHIS.FOIA@usda.gov",
        "portal": "https://efoia-pal.usda.gov/App/Home.aspx",
        "phone": "(301) 851-4102",
        "notes": "Handles Animal Welfare Act inspection and enforcement records.",
    },
    "USDA-FSIS": {
        "full_name": "United States Department of Agriculture — "
                     "Food Safety and Inspection Service",
        "foia_officer": "FOIA Officer, Office of Public Affairs and Consumer Education",
        "address": "1400 Independence Ave SW, Room 2534-S, Washington, DC 20250",
        "email": "fsis.foia@usda.gov",
        "portal": "https://efoia-pal.usda.gov/App/Home.aspx",
        "phone": "(202) 720-2109",
        "notes": "Handles slaughterhouse inspection reports, NRs, MOIs.",
    },
    "USDA-AMS": {
        "full_name": "United States Department of Agriculture — "
                     "Agricultural Marketing Service",
        "foia_officer": "FOIA Coordinator",
        "address": "1400 Independence Ave SW, Room 3521-S, Washington, DC 20250",
        "email": "AMS.FOIA@usda.gov",
        "portal": "https://efoia-pal.usda.gov/App/Home.aspx",
        "phone": "(202) 720-8164",
        "notes": "Grading, commodity purchases, organic program records.",
    },
    "USDA-FSA": {
        "full_name": "United States Department of Agriculture — "
                     "Farm Service Agency",
        "foia_officer": "FOIA Officer",
        "address": "1400 Independence Ave SW, Stop 0506, Washington, DC 20250",
        "email": "FSA.FOIA@usda.gov",
        "portal": "https://efoia-pal.usda.gov/App/Home.aspx",
        "phone": "(202) 720-3438",
        "notes": "Subsidy payments, disaster assistance, farm program data.",
    },
    "EPA": {
        "full_name": "United States Environmental Protection Agency",
        "foia_officer": "National FOIA Office",
        "address": "1200 Pennsylvania Ave NW (2822T), Washington, DC 20460",
        "email": "hq.foia@epa.gov",
        "portal": "https://www.epa.gov/foia/how-submit-foia-request",
        "phone": "(202) 566-1667",
        "notes": "CAFO permits, water quality violations, manure management plans.",
    },
    "FDA": {
        "full_name": "United States Food and Drug Administration",
        "foia_officer": "Division of Freedom of Information",
        "address": "12420 Parklawn Dr, Element Bldg, Room 1050, Rockville, MD 20857",
        "email": "FDAFOIA@fda.hhs.gov",
        "portal": "https://www.accessdata.fda.gov/scripts/foi/FOIRequest/requestinfo.cfm",
        "phone": "(301) 796-3900",
        "notes": "Drug approval records, residue testing, medicated feed applications.",
    },
    "OSHA": {
        "full_name": "Occupational Safety and Health Administration",
        "foia_officer": "FOIA Disclosure Officer",
        "address": "200 Constitution Ave NW, Room N-3647, Washington, DC 20210",
        "email": "FOIA-OSHA@dol.gov",
        "portal": "https://www.osha.gov/foia",
        "phone": "(202) 693-2197",
        "notes": "Workplace injury logs, inspection records at slaughterhouses, CAFOs.",
    },
    "USDA-NRCS": {
        "full_name": "United States Department of Agriculture — "
                     "Natural Resources Conservation Service",
        "foia_officer": "FOIA Coordinator",
        "address": "1400 Independence Ave SW, Room 6121-S, Washington, DC 20250",
        "email": "NRCS.FOIA@usda.gov",
        "portal": "https://efoia-pal.usda.gov/App/Home.aspx",
        "phone": "(202) 720-4525",
        "notes": "EQIP payments for animal waste systems, conservation plans.",
    },
}


# ---------------------------------------------------------------------------
# Jinja2 master template
# ---------------------------------------------------------------------------

FOIA_REQUEST_TEMPLATE = """\
{{ filing_date }}

{{ agency_info.foia_officer }}
{{ agency_info.full_name }}
{{ agency_info.address }}

{% if agency_info.email %}Via email: {{ agency_info.email }}{% endif %}

Re: Freedom of Information Act Request

Dear FOIA Officer:

Pursuant to the Freedom of Information Act (FOIA), 5 U.S.C. § 552, \
and the implementing regulations of the {{ agency_info.full_name }}, \
I respectfully request copies of the following records:

{% if template_description %}
{{ template_description }}
{% endif %}

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
format. Pursuant to 5 U.S.C. § 552(a)(3)(B), agencies must provide records \
in any form or format requested if the record is readily reproducible in \
that form or format.

{% if fee_waiver %}
FEE WAIVER REQUEST:

Pursuant to 5 U.S.C. § 552(a)(4)(A)(iii), I request a waiver of all fees \
associated with this request. Disclosure of the requested information is in \
the public interest because it is likely to contribute significantly to public \
understanding of the operations or activities of the government and is not \
primarily in the commercial interest of the requester.

{{ requester_org }} is a nonprofit research organization dedicated to \
government transparency and public accountability in animal agriculture \
policy. The information obtained will be analyzed and disseminated to the \
general public through published reports, educational materials, and press \
releases. The requester has the ability and intention to effectively convey \
the information to the public. The requester has no commercial interest in \
the requested records.

If a full fee waiver is not granted, I request that I be classified as a \
representative of the news media or an educational institution under \
5 U.S.C. § 552(a)(4)(A)(ii), which limits fees to reasonable standard \
charges for document duplication. In the alternative, I am willing to pay \
fees up to $25.00. If estimated fees exceed this amount, please contact me \
before proceeding.
{% endif %}

{% if expedited %}
EXPEDITED PROCESSING:

Pursuant to 5 U.S.C. § 552(a)(6)(E), I request expedited processing of this \
request. There is a compelling need for the records because the information \
is urgently needed to inform the public concerning actual or alleged federal \
government activity, and the request is made by a person primarily engaged \
in disseminating information to the public.
{% endif %}

RESPONSE DEADLINE: FOIA requires agencies to respond within twenty (20) \
business days of receipt of a request. 5 U.S.C. § 552(a)(6)(A)(i).

If any responsive records are withheld in whole or in part, I request that \
you identify the records withheld, state the specific exemption(s) under \
5 U.S.C. § 552(b) justifying each withholding, and release all reasonably \
segregable non-exempt portions. See 5 U.S.C. § 552(b) (final sentence).

{% if additional_notes %}
ADDITIONAL INFORMATION: {{ additional_notes }}
{% endif %}

I look forward to your response within the statutory time frame. If you have \
any questions regarding this request, please contact me at the address below.

Sincerely,

{{ requester_name }}
{% if requester_org %}{{ requester_org }}{% endif %}
{% if requester_address %}{{ requester_address }}{% endif %}
{% if requester_email %}{{ requester_email }}{% endif %}
{% if requester_phone %}{{ requester_phone }}{% endif %}
"""


class USFederalGenerator(RequestGenerator):
    """Generate FOIA requests for US federal agencies."""

    def __init__(self) -> None:
        super().__init__(templates_file="us_federal_templates.json")

    # ---- public interface ----

    def generate(self, context: RequestContext) -> GeneratedRequest:
        agency_key = self._resolve_agency_key(context.agency)
        agency_info = US_FEDERAL_AGENCIES.get(agency_key)
        if agency_info is None:
            raise ValueError(
                f"Unknown agency '{context.agency}'. Known agencies: "
                f"{', '.join(US_FEDERAL_AGENCIES.keys())}"
            )

        template_description = ""
        if context.template_id:
            tpl = self.get_template(context.template_id)
            if tpl:
                template_description = tpl.get("description", "")
                # Merge template-specified records with any user-provided ones
                context.specific_records = (
                    tpl.get("records", []) + context.specific_records
                )
                if not context.keywords and tpl.get("keywords"):
                    context.keywords = tpl["keywords"]

        text = self._render(
            FOIA_REQUEST_TEMPLATE,
            context,
            agency_info=agency_info,
            template_description=template_description,
            fee_waiver=context.fee_waiver,
            expedited=context.expedited_processing,
        )

        filing_method = "email"
        if agency_info.get("portal"):
            filing_method = "online portal preferred; email accepted"

        return GeneratedRequest(
            text=text.strip(),
            jurisdiction="US-Federal",
            agency=agency_info["full_name"],
            legal_basis="Freedom of Information Act, 5 U.S.C. § 552",
            estimated_deadline_days=20,
            filing_method=filing_method,
            fee_notes=(
                "Fee waiver requested under 5 U.S.C. § 552(a)(4)(A)(iii). "
                "Fallback: $25 cap unless requester contacted."
            ),
            context=context,
            metadata={
                "agency_key": agency_key,
                "agency_email": agency_info.get("email", ""),
                "agency_portal": agency_info.get("portal", ""),
            },
        )

    def get_agencies(self) -> dict[str, dict[str, str]]:
        return US_FEDERAL_AGENCIES

    def get_legal_basis(self) -> str:
        return (
            "Freedom of Information Act (FOIA), 5 U.S.C. § 552, as amended. "
            "Enacted 1966; major amendments in 1974, 1996 (E-FOIA), "
            "2007 (OPEN Government Act), and 2016 (FOIA Improvement Act)."
        )

    def get_fee_waiver_language(self, context: RequestContext) -> str:
        return (
            "Pursuant to 5 U.S.C. § 552(a)(4)(A)(iii), I request a waiver of all "
            "fees. Disclosure is in the public interest because it is likely to "
            "contribute significantly to public understanding of government operations "
            "and is not primarily in the commercial interest of the requester. "
            f"{context.requester_organization} is a nonprofit organization dedicated to "
            "transparency in animal agriculture policy."
        )

    def get_appeal_info(self) -> dict[str, str]:
        return {
            "basis": (
                "Under 5 U.S.C. § 552(a)(6)(A), a requester may appeal any adverse "
                "determination to the head of the agency within 90 days (or as "
                "specified by the agency's regulations)."
            ),
            "next_step": (
                "If the administrative appeal is denied, the requester may seek "
                "judicial review by filing suit in the US District Court under "
                "5 U.S.C. § 552(a)(4)(B)."
            ),
            "ogis": (
                "The Office of Government Information Services (OGIS) within the "
                "National Archives offers free mediation services as a non-exclusive "
                "alternative to litigation. Contact: ogis@nara.gov, (202) 741-5770."
            ),
        }

    # ---- internals ----

    def _resolve_agency_key(self, raw: str) -> str:
        """Fuzzy-match user input to a canonical agency key."""
        upper = raw.upper().strip()
        # Direct match
        if upper in US_FEDERAL_AGENCIES:
            return upper
        # Common aliases
        aliases: dict[str, str] = {
            "USDA": "USDA-APHIS",
            "APHIS": "USDA-APHIS",
            "FSIS": "USDA-FSIS",
            "AMS": "USDA-AMS",
            "FSA": "USDA-FSA",
            "NRCS": "USDA-NRCS",
        }
        if upper in aliases:
            return aliases[upper]
        # Substring search
        for key in US_FEDERAL_AGENCIES:
            if upper in key or key in upper:
                return key
        return raw
