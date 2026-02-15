"""
UK Freedom of Information Act 2000 request generator.

Generates FOI requests under the Freedom of Information Act 2000 (c. 36)
and the Environmental Information Regulations 2004 (SI 2004/3391) for
UK public authorities involved in animal agriculture and food safety.
"""

from __future__ import annotations

from typing import Any, Optional

from foia_rti.generators.generator_base import (
    GeneratedRequest,
    RequestContext,
    RequestGenerator,
)


UK_AGENCIES: dict[str, dict[str, str]] = {
    "DEFRA": {
        "full_name": "Department for Environment, Food and Rural Affairs",
        "foi_email": "defra.foi@defra.gov.uk",
        "address": "Seacole Building, 2 Marsham Street, London SW1P 4DF",
        "notes": (
            "Farm inspections, animal welfare enforcement, "
            "livestock subsidy data (post-Brexit farm payments), "
            "disease outbreak records (avian flu, bovine TB)."
        ),
    },
    "FSA": {
        "full_name": "Food Standards Agency",
        "foi_email": "foi@food.gov.uk",
        "address": "Floors 6 and 7, Clive House, 70 Petty France, London SW1H 9EX",
        "notes": (
            "Slaughterhouse inspection reports, CCTV compliance data, "
            "meat hygiene enforcement, approved establishment lists."
        ),
    },
    "EA": {
        "full_name": "Environment Agency",
        "foi_email": "enquiries@environment-agency.gov.uk",
        "address": "Horizon House, Deanery Road, Bristol BS1 5AH",
        "notes": (
            "Environmental permits for intensive livestock units, "
            "water discharge consents, pollution incident reports, "
            "ammonia emission data from farms."
        ),
    },
    "APHA": {
        "full_name": "Animal and Plant Health Agency",
        "foi_email": "foi@apha.gov.uk",
        "address": "Woodham Lane, New Haw, Addlestone, Surrey KT15 3NB",
        "notes": (
            "Disease surveillance reports, TB testing data, "
            "import/export health certificates, welfare at slaughter enforcement."
        ),
    },
    "VMD": {
        "full_name": "Veterinary Medicines Directorate",
        "foi_email": "foi@vmd.gov.uk",
        "address": "Woodham Lane, New Haw, Addlestone, Surrey KT15 3LS",
        "notes": (
            "Antimicrobial usage data, veterinary drug residue testing, "
            "marketing authorization records."
        ),
    },
    "NRW": {
        "full_name": "Natural Resources Wales",
        "foi_email": "foi@naturalresourceswales.gov.uk",
        "address": "Ty Cambria, 29 Newport Road, Cardiff CF24 0TP",
        "notes": "Welsh environmental permits, agricultural pollution incidents.",
    },
    "SEPA": {
        "full_name": "Scottish Environment Protection Agency",
        "foi_email": "foi@sepa.org.uk",
        "address": "Strathallan House, Castle Business Park, Stirling FK9 4TZ",
        "notes": "Scottish CAR licences, waste management from livestock operations.",
    },
}


UK_FOI_TEMPLATE = """\
{{ filing_date }}

{{ agency_full_name }}
{% if agency_address %}{{ agency_address }}{% endif %}

{% if agency_email %}Via email: {{ agency_email }}{% endif %}

Dear Sir or Madam,

FREEDOM OF INFORMATION REQUEST

I am writing to make a request for information under the Freedom of \
Information Act 2000 (the "Act").

{% if eir %}
To the extent that any of the information requested falls within the \
definition of "environmental information" under the Environmental \
Information Regulations 2004 (SI 2004/3391), I also make this request \
under those Regulations.
{% endif %}

I request the following information:

{% for record in specific_records %}
{{ loop.index }}. {{ record }}
{% endfor %}

{% if keywords %}
Specifically, I request information relating to the following subjects: \
{{ keywords | join(', ') }}.
{% endif %}

{% if facilities %}
This request relates to the following establishments or locations: \
{{ facilities | join('; ') }}.
{% endif %}

TIME PERIOD: {{ date_range }}.

FORMAT: I would prefer to receive the information in {{ preferred_format }} \
format, pursuant to Section 11 of the Act.

Under Section 10(1) of the Freedom of Information Act 2000, you are \
required to respond to this request promptly and in any event not later \
than twenty (20) working days after the date of receipt.

If you consider that any of the information requested is exempt from \
disclosure, I request that you:
(a) identify the specific exemption(s) relied upon under Part II of the Act;
(b) explain why the public interest in maintaining the exemption outweighs \
the public interest in disclosure, where the exemption is a qualified one \
(Section 2(2)(b)); and
(c) confirm whether or not the information is held, unless to do so would \
itself reveal exempt information (Section 1(1)(a)).

If this request is refused in whole or in part, I intend to request an \
internal review under the Act's Section 45 Code of Practice, and if \
necessary, to complain to the Information Commissioner's Office.

{% if additional_notes %}
Additional information: {{ additional_notes }}
{% endif %}

I look forward to your response within the statutory time frame.

Yours faithfully,

{{ requester_name }}
{% if requester_org %}{{ requester_org }}{% endif %}
{% if requester_address %}{{ requester_address }}{% endif %}
{% if requester_email %}{{ requester_email }}{% endif %}
{% if requester_phone %}{{ requester_phone }}{% endif %}
"""


class UKFOIGenerator(RequestGenerator):
    """Generate FOI requests under the UK Freedom of Information Act 2000."""

    def __init__(self) -> None:
        super().__init__()

    def generate(self, context: RequestContext, eir: bool = True) -> GeneratedRequest:
        agency_key = self._resolve_agency(context.agency)
        agency_info = UK_AGENCIES.get(agency_key)
        if agency_info is None:
            raise ValueError(
                f"Unknown agency '{context.agency}'. Known agencies: "
                f"{', '.join(UK_AGENCIES.keys())}"
            )

        text = self._render(
            UK_FOI_TEMPLATE,
            context,
            agency_full_name=agency_info["full_name"],
            agency_address=agency_info.get("address", ""),
            agency_email=agency_info.get("foi_email", ""),
            eir=eir,
        )

        return GeneratedRequest(
            text=text.strip(),
            jurisdiction="UK",
            agency=agency_info["full_name"],
            legal_basis=(
                "Freedom of Information Act 2000, Section 1; "
                "Environmental Information Regulations 2004 (if applicable)"
            ),
            estimated_deadline_days=20,
            filing_method="email",
            fee_notes=(
                "No application fee for FOI requests. If estimated cost exceeds "
                "the 'appropriate limit' (currently GBP 600 for central government, "
                "GBP 450 for other authorities — Freedom of Information and Data "
                "Protection (Appropriate Limit and Fees) Regulations 2004), the "
                "authority may refuse or charge. Disbursement costs (printing, "
                "postage) may be charged at cost. EIR requests cannot be refused "
                "on cost grounds alone — must balance public interest."
            ),
            context=context,
            metadata={
                "agency_key": agency_key,
                "agency_email": agency_info.get("foi_email", ""),
                "eir_included": eir,
            },
        )

    def get_agencies(self) -> dict[str, dict[str, str]]:
        return UK_AGENCIES

    def get_legal_basis(self) -> str:
        return (
            "Freedom of Information Act 2000 (c. 36). "
            "Environmental Information Regulations 2004 (SI 2004/3391). "
            "Section 1: general right of access. Section 10: 20 working day deadline. "
            "Section 17: refusal notice must cite specific exemptions. "
            "Part II (Sections 21-44): exemptions. "
            "Information Commissioner: ico.org.uk."
        )

    def get_fee_waiver_language(self, context: RequestContext) -> str:
        return (
            "FOI requests in the UK do not carry an application fee. "
            "If the cost exceeds the 'appropriate limit,' the authority may "
            "ask the requester to narrow the request. No fee waiver mechanism "
            "equivalent to US FOIA exists; instead, challenge any charge as "
            "exceeding the Fees Regulations."
        )

    def get_appeal_info(self) -> dict[str, str]:
        return {
            "internal_review": (
                "Under the Section 45 Code of Practice, the first step is to "
                "request an internal review from the public authority. There is "
                "no statutory time limit for requesting internal review, but "
                "the ICO recommends doing so within 40 working days of the "
                "original response."
            ),
            "ico_complaint": (
                "If the internal review is unsatisfactory, complain to the "
                "Information Commissioner's Office (ICO). The ICO can issue "
                "a Decision Notice ordering disclosure. Contact: "
                "https://ico.org.uk/make-a-complaint/"
            ),
            "tribunal": (
                "Either party may appeal an ICO Decision Notice to the "
                "First-tier Tribunal (Information Rights) within 28 days, "
                "and from there to the Upper Tribunal on a point of law."
            ),
        }

    @staticmethod
    def _resolve_agency(raw: str) -> str:
        upper = raw.upper().strip()
        if upper in UK_AGENCIES:
            return upper
        aliases: dict[str, str] = {
            "ENVIRONMENT AGENCY": "EA",
            "FOOD STANDARDS": "FSA",
            "FOOD STANDARDS AGENCY": "FSA",
            "ANIMAL AND PLANT HEALTH": "APHA",
            "VETERINARY MEDICINES": "VMD",
            "NATURAL RESOURCES WALES": "NRW",
        }
        for alias, key in aliases.items():
            if alias in upper:
                return key
        return raw
