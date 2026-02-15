"""
India Right to Information (RTI) Act 2005 request generator.

Generates RTI applications under the Right to Information Act, 2005
(Act No. 22 of 2005), targeting Indian public authorities involved
in animal welfare, food safety, and environmental regulation.

Supports bilingual output (English and Hindi).
"""

from __future__ import annotations

from typing import Any, Optional

from foia_rti.generators.generator_base import (
    GeneratedRequest,
    RequestContext,
    RequestGenerator,
)


# ---------------------------------------------------------------------------
# Public authority registry
# ---------------------------------------------------------------------------

INDIA_AGENCIES: dict[str, dict[str, str]] = {
    "AWBI": {
        "full_name": "Animal Welfare Board of India",
        "hindi_name": "भारतीय पशु कल्याण बोर्ड",
        "address": "13/1, Third Seaward Road, Valmiki Nagar, Thiruvanmiyur, Chennai 600041",
        "pio_designation": "Public Information Officer",
        "parent_ministry": "Ministry of Fisheries, Animal Husbandry and Dairying",
        "notes": (
            "Oversees implementation of Prevention of Cruelty to Animals Act, 1960. "
            "Key records: slaughterhouse inspection reports, ABC programme data, "
            "recognition/de-recognition of AWOs."
        ),
    },
    "FSSAI": {
        "full_name": "Food Safety and Standards Authority of India",
        "hindi_name": "भारतीय खाद्य सुरक्षा एवं मानक प्राधिकरण",
        "address": "FDA Bhawan, Kotla Road, New Delhi 110002",
        "pio_designation": "Central Public Information Officer",
        "parent_ministry": "Ministry of Health and Family Welfare",
        "notes": (
            "Food safety licensing, inspection of meat and dairy processing "
            "units, antibiotic residue testing data."
        ),
    },
    "CPCB": {
        "full_name": "Central Pollution Control Board",
        "hindi_name": "केन्द्रीय प्रदूषण नियंत्रण बोर्ड",
        "address": "Parivesh Bhawan, East Arjun Nagar, Delhi 110032",
        "pio_designation": "Central Public Information Officer",
        "parent_ministry": "Ministry of Environment, Forest and Climate Change",
        "notes": (
            "Industrial effluent from tanneries and slaughterhouses, "
            "CAFO-equivalent pollution data, EIA clearances."
        ),
    },
    "DAHD": {
        "full_name": "Department of Animal Husbandry and Dairying",
        "hindi_name": "पशुपालन एवं डेयरी विभाग",
        "address": "Krishi Bhawan, New Delhi 110001",
        "pio_designation": "Central Public Information Officer",
        "parent_ministry": "Ministry of Fisheries, Animal Husbandry and Dairying",
        "notes": (
            "National livestock census data, subsidy disbursements for dairy, "
            "poultry and pig development schemes."
        ),
    },
    "MoEFCC": {
        "full_name": "Ministry of Environment, Forest and Climate Change",
        "hindi_name": "पर्यावरण, वन एवं जलवायु परिवर्तन मंत्रालय",
        "address": "Indira Paryavaran Bhawan, Jor Bagh Road, New Delhi 110003",
        "pio_designation": "Central Public Information Officer",
        "parent_ministry": "Direct ministry",
        "notes": (
            "Environmental clearances for large-scale livestock operations, "
            "wildlife trade permits, Project Elephant data."
        ),
    },
    "SPCB": {
        "full_name": "State Pollution Control Board (generic — specify state)",
        "hindi_name": "राज्य प्रदूषण नियंत्रण बोर्ड",
        "address": "Varies by state",
        "pio_designation": "Public Information Officer",
        "parent_ministry": "State government",
        "notes": (
            "Consent-to-operate for slaughterhouses and tanneries, "
            "effluent monitoring data, compliance/show-cause orders."
        ),
    },
    "APEDA": {
        "full_name": "Agricultural and Processed Food Products Export Development Authority",
        "hindi_name": "कृषि एवं प्रसंस्कृत खाद्य उत्पाद निर्यात विकास प्राधिकरण",
        "address": "NCUI Building, 3rd Floor, 3 Siri Institutional Area, New Delhi 110016",
        "pio_designation": "Public Information Officer",
        "parent_ministry": "Ministry of Commerce and Industry",
        "notes": "Meat and dairy export data, registered export units, traceability data.",
    },
}


# ---------------------------------------------------------------------------
# RTI application template — bilingual English / Hindi
# ---------------------------------------------------------------------------

RTI_TEMPLATE_ENGLISH = """\
APPLICATION UNDER THE RIGHT TO INFORMATION ACT, 2005
(सूचना का अधिकार अधिनियम, 2005 के तहत आवेदन)

To,
The {{ pio_designation }},
{{ agency_full_name }}
{% if agency_hindi_name %}({{ agency_hindi_name }}){% endif %}
{{ agency_address }}

Date: {{ filing_date }}

Subject: Application under Section 6 of the Right to Information Act, 2005

Sir/Madam,

I, {{ requester_name }}, hereby submit this application under Section 6(1) \
of the Right to Information Act, 2005 (Act No. 22 of 2005), and request the \
following information:

{% for record in specific_records %}
{{ loop.index }}. {{ record }}
{% endfor %}

{% if keywords %}
The above request specifically concerns the following subjects: \
{{ keywords | join(', ') }}.
{% endif %}

{% if facilities %}
This request relates to the following establishments/facilities: \
{{ facilities | join('; ') }}.
{% endif %}

PERIOD: {{ date_range }}.

FORMAT: I request that the information be provided in {{ preferred_format }} \
format, as permitted under Section 7(9) of the RTI Act.

FEE: An application fee of Rs. 10/- (Rupees Ten only) is enclosed herewith \
{% if fee_mode == 'ipo' %}\
by Indian Postal Order (IPO) No. __________ payable to the accounts officer \
of {{ agency_full_name }}.
{% elif fee_mode == 'dd' %}\
by Demand Draft payable to the accounts officer of {{ agency_full_name }}.
{% elif fee_mode == 'online' %}\
via online payment on the RTI Online Portal.
{% else %}\
by Indian Postal Order / Demand Draft / Cash (as applicable).
{% endif %}

{% if bpl %}
Note: I belong to a Below Poverty Line (BPL) family and am exempt from \
payment of fees under Section 7(5) of the RTI Act. A copy of my BPL \
certificate is attached.
{% endif %}

As per Section 7(1) of the RTI Act, 2005, the information must be provided \
within thirty (30) days from the date of receipt of this application. If \
the information concerns the life or liberty of a person, the time limit is \
forty-eight (48) hours under Section 7(1) proviso.

If this application or any part thereof falls under the jurisdiction of \
another public authority, I request that the concerned portion be transferred \
under Section 6(3) within five (5) days.

If the information is denied or not provided within the statutory time limit, \
I reserve the right to file a first appeal under Section 19(1) to the First \
Appellate Authority, and thereafter a second appeal to the Central Information \
Commission / State Information Commission under Section 19(3).

{% if additional_notes %}
Additional remarks: {{ additional_notes }}
{% endif %}

Yours faithfully,

{{ requester_name }}
{% if requester_org %}Organization: {{ requester_org }}{% endif %}
{% if requester_address %}Address: {{ requester_address }}{% endif %}
{% if requester_email %}Email: {{ requester_email }}{% endif %}
{% if requester_phone %}Phone: {{ requester_phone }}{% endif %}
"""

RTI_TEMPLATE_HINDI = """\
सूचना का अधिकार अधिनियम, 2005 के तहत आवेदन
(APPLICATION UNDER THE RIGHT TO INFORMATION ACT, 2005)

सेवा में,
{{ pio_designation }},
{{ agency_hindi_name }}
({{ agency_full_name }})
{{ agency_address }}

दिनांक: {{ filing_date }}

विषय: सूचना का अधिकार अधिनियम, 2005 की धारा 6 के तहत आवेदन

महोदय / महोदया,

मैं, {{ requester_name }}, सूचना का अधिकार अधिनियम, 2005 (अधिनियम संख्या 22, \
2005) की धारा 6(1) के तहत यह आवेदन प्रस्तुत करता/करती हूँ और निम्नलिखित \
सूचना की माँग करता/करती हूँ:

{% for record in specific_records %}
{{ loop.index }}. {{ record }}
{% endfor %}

{% if keywords %}
उपरोक्त अनुरोध विशेष रूप से निम्नलिखित विषयों से संबंधित है: \
{{ keywords | join(', ') }}.
{% endif %}

अवधि: {{ date_range }}.

प्रारूप: कृपया सूचना {{ preferred_format }} प्रारूप में प्रदान करें।

शुल्क: इस आवेदन के साथ रु. 10/- (दस रुपये मात्र) का शुल्क संलग्न है।

धारा 7(1) के अनुसार, सूचना आवेदन प्राप्ति के तीस (30) दिनों के भीतर \
प्रदान की जानी चाहिए।

भवदीय,

{{ requester_name }}
{% if requester_org %}संस्था: {{ requester_org }}{% endif %}
{% if requester_address %}पता: {{ requester_address }}{% endif %}
{% if requester_email %}ईमेल: {{ requester_email }}{% endif %}
{% if requester_phone %}दूरभाष: {{ requester_phone }}{% endif %}
"""


class IndiaRTIGenerator(RequestGenerator):
    """Generate RTI applications under the Right to Information Act, 2005."""

    def __init__(self) -> None:
        super().__init__(templates_file="india_rti_templates.json")

    def generate(
        self,
        context: RequestContext,
        language: str = "english",
        fee_mode: str = "ipo",
        bpl: bool = False,
    ) -> GeneratedRequest:
        agency_key = self._resolve_agency(context.agency)
        agency_info = INDIA_AGENCIES.get(agency_key)
        if agency_info is None:
            raise ValueError(
                f"Unknown agency '{context.agency}'. Known agencies: "
                f"{', '.join(INDIA_AGENCIES.keys())}"
            )

        template_description = ""
        if context.template_id:
            tpl = self.get_template(context.template_id)
            if tpl:
                template_description = tpl.get("description", "")
                context.specific_records = (
                    tpl.get("records", []) + context.specific_records
                )
                if not context.keywords and tpl.get("keywords"):
                    context.keywords = tpl["keywords"]

        tpl_str = RTI_TEMPLATE_HINDI if language.lower() == "hindi" else RTI_TEMPLATE_ENGLISH

        text = self._render(
            tpl_str,
            context,
            pio_designation=agency_info.get("pio_designation", "Public Information Officer"),
            agency_full_name=agency_info["full_name"],
            agency_hindi_name=agency_info.get("hindi_name", ""),
            agency_address=agency_info["address"],
            fee_mode=fee_mode,
            bpl=bpl,
            template_description=template_description,
        )

        return GeneratedRequest(
            text=text.strip(),
            jurisdiction="India",
            agency=agency_info["full_name"],
            legal_basis="Right to Information Act, 2005, Section 6(1)",
            estimated_deadline_days=30,
            filing_method=(
                "Post / hand delivery / RTI Online Portal "
                "(https://rtionline.gov.in) for central government bodies"
            ),
            fee_notes=(
                "Application fee: Rs. 10/- via IPO, DD, court fee stamp, or "
                "online payment. BPL applicants are exempt (Section 7(5)). "
                "Additional fees for copies: Rs. 2/- per A4 page, Rs. 50/- per "
                "diskette/CD (as per RTI Fee Rules, 2005)."
            ),
            context=context,
            metadata={
                "agency_key": agency_key,
                "language": language,
                "parent_ministry": agency_info.get("parent_ministry", ""),
            },
        )

    def get_agencies(self) -> dict[str, dict[str, str]]:
        return INDIA_AGENCIES

    def get_legal_basis(self) -> str:
        return (
            "Right to Information Act, 2005 (Act No. 22 of 2005). "
            "Key sections: Section 3 (right of citizens), Section 6 (application), "
            "Section 7 (disposal within 30 days), Section 8 (exemptions), "
            "Section 19 (appeals). First Appellate Authority within the public "
            "authority; second appeal to the Central/State Information Commission."
        )

    def get_fee_waiver_language(self, context: RequestContext) -> str:
        return (
            "Under Section 7(5) of the RTI Act, 2005, no fee shall be charged "
            "from persons who are below the poverty line as may be determined by "
            "the appropriate Government. If the applicant belongs to a BPL family, "
            "attach a copy of the BPL ration card or certificate."
        )

    def get_appeal_info(self) -> dict[str, str]:
        return {
            "first_appeal": (
                "Under Section 19(1), a first appeal lies to the officer senior "
                "in rank to the CPIO/SPIO within the public authority, within "
                "30 days of the expiry of the response period or receipt of the "
                "decision. The First Appellate Authority must dispose of the "
                "appeal within 30 days (extendable to 45 days with reasons)."
            ),
            "second_appeal": (
                "Under Section 19(3), a second appeal lies to the Central "
                "Information Commission (for central authorities) or the State "
                "Information Commission (for state authorities), within 90 days "
                "of the first appellate decision."
            ),
            "penalties": (
                "Section 20: The Information Commission may impose a penalty of "
                "Rs. 250/- per day (up to Rs. 25,000/-) on the CPIO for failure "
                "to provide information without reasonable cause."
            ),
            "cic_contact": (
                "Central Information Commission: CIC Bhawan, Baba Gang Nath "
                "Marg, Munirka, New Delhi 110067. Phone: 011-26182583."
            ),
        }

    @staticmethod
    def _resolve_agency(raw: str) -> str:
        upper = raw.upper().strip()
        if upper in INDIA_AGENCIES:
            return upper
        aliases: dict[str, str] = {
            "ANIMAL WELFARE BOARD": "AWBI",
            "FOOD SAFETY": "FSSAI",
            "POLLUTION CONTROL": "CPCB",
            "CENTRAL POLLUTION": "CPCB",
            "STATE POLLUTION": "SPCB",
            "ANIMAL HUSBANDRY": "DAHD",
            "ENVIRONMENT": "MoEFCC",
            "MOEF": "MoEFCC",
        }
        for alias, key in aliases.items():
            if alias in upper:
                return key
        return raw
