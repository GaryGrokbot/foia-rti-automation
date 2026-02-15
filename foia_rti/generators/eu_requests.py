"""
EU access-to-documents request generator.

Generates requests under Regulation (EC) No 1049/2001 of the European
Parliament and of the Council of 30 May 2001 regarding public access
to European Parliament, Council and Commission documents.

Also references the Aarhus Regulation (EC) No 1367/2006 for environmental
information held by EU institutions.
"""

from __future__ import annotations

from typing import Any, Optional

from foia_rti.generators.generator_base import (
    GeneratedRequest,
    RequestContext,
    RequestGenerator,
)


EU_INSTITUTIONS: dict[str, dict[str, str]] = {
    "EC-DG-SANTE": {
        "full_name": "European Commission — Directorate-General for Health and Food Safety (DG SANTE)",
        "address": "European Commission, B-1049 Brussels, Belgium",
        "email": "sg-acc-doc@ec.europa.eu",
        "portal": "https://ec.europa.eu/info/about-european-commission/contact/problems-and-complaints/how-make-request-access-european-commission-documents_en",
        "notes": (
            "Animal welfare legislation (Regulation (EC) 1099/2009 on slaughter, "
            "Directive 98/58/EC on farm animals), FVO/DG SANTE audit reports, "
            "antimicrobial resistance data, food chain contaminant reports."
        ),
    },
    "EC-DG-AGRI": {
        "full_name": "European Commission — Directorate-General for Agriculture and Rural Development (DG AGRI)",
        "address": "European Commission, B-1049 Brussels, Belgium",
        "email": "sg-acc-doc@ec.europa.eu",
        "portal": "https://ec.europa.eu/info/about-european-commission/contact/problems-and-complaints/how-make-request-access-european-commission-documents_en",
        "notes": (
            "Common Agricultural Policy (CAP) payment data, farm subsidy records, "
            "market intervention measures, rural development programme evaluations."
        ),
    },
    "EC-DG-ENV": {
        "full_name": "European Commission — Directorate-General for Environment (DG ENV)",
        "address": "European Commission, B-1049 Brussels, Belgium",
        "email": "sg-acc-doc@ec.europa.eu",
        "portal": "https://ec.europa.eu/info/about-european-commission/contact/problems-and-complaints/how-make-request-access-european-commission-documents_en",
        "notes": (
            "Industrial Emissions Directive compliance for large livestock farms, "
            "Nitrates Directive implementation, biodiversity impact assessments, "
            "infringement proceedings against Member States."
        ),
    },
    "EFSA": {
        "full_name": "European Food Safety Authority",
        "address": "Via Carlo Magno 1A, 43126 Parma, Italy",
        "email": "access-to-documents@efsa.europa.eu",
        "portal": "https://www.efsa.europa.eu/en/access-to-documents",
        "notes": (
            "Risk assessments, scientific opinions on animal welfare (e.g., "
            "cage-free housing, transport conditions, slaughter methods), "
            "antimicrobial resistance monitoring data."
        ),
    },
    "ECA": {
        "full_name": "European Court of Auditors",
        "address": "12, rue Alcide De Gasperi, 1615 Luxembourg",
        "email": "eca-info@eca.europa.eu",
        "portal": "https://www.eca.europa.eu/en/Pages/AccessToDocuments.aspx",
        "notes": (
            "Audit reports on CAP spending, compliance evaluations of "
            "animal welfare payments, value-for-money assessments."
        ),
    },
    "EU-COUNCIL": {
        "full_name": "Council of the European Union",
        "address": "Rue de la Loi 175, B-1048 Brussels, Belgium",
        "email": "access@consilium.europa.eu",
        "portal": "https://www.consilium.europa.eu/en/documents-publications/access-documents/",
        "notes": (
            "Working party documents on animal welfare proposals, "
            "Council position papers, trilogue negotiations."
        ),
    },
    "EU-PARLIAMENT": {
        "full_name": "European Parliament",
        "address": "Rue Wiertz 60, B-1047 Brussels, Belgium",
        "email": "accesdoc@europarl.europa.eu",
        "portal": "https://www.europarl.europa.eu/RegistreWeb/home/welcome.htm",
        "notes": (
            "Committee meeting minutes (AGRI, ENVI committees), "
            "amendment proposals, parliamentary questions and answers."
        ),
    },
}


EU_REQUEST_TEMPLATE = """\
{{ filing_date }}

{{ agency_full_name }}
{{ agency_address }}

{% if agency_email %}Via email: {{ agency_email }}{% endif %}

APPLICATION FOR ACCESS TO DOCUMENTS
Regulation (EC) No 1049/2001

Dear Sir or Madam,

Pursuant to Regulation (EC) No 1049/2001 of the European Parliament and of \
the Council of 30 May 2001 regarding public access to European Parliament, \
Council and Commission documents, I hereby request access to the following \
documents:

{% for record in specific_records %}
{{ loop.index }}. {{ record }}
{% endfor %}

{% if keywords %}
I also request any documents containing or substantively relating to the \
following terms or subjects: {{ keywords | join(', ') }}.
{% endif %}

{% if facilities %}
This request relates to the following entities or programmes: \
{{ facilities | join('; ') }}.
{% endif %}

TIME PERIOD: {{ date_range }}.

{% if aarhus %}
ENVIRONMENTAL INFORMATION: To the extent that the requested documents \
contain environmental information within the meaning of Regulation (EC) \
No 1367/2006 (the Aarhus Regulation), I also rely on the provisions of \
that Regulation, which requires a broad interpretation of the right of \
access to environmental information and a narrow interpretation of \
exceptions.
{% endif %}

FORMAT: Pursuant to Article 10(3) of Regulation 1049/2001, I request that \
the documents be made available in {{ preferred_format }} format.

Under Article 7(1) of Regulation 1049/2001, you are required to respond to \
this application within fifteen (15) working days of its registration. \
This time limit may be extended by a further fifteen (15) working days \
under Article 7(3), provided that the applicant is informed in advance \
with detailed reasons.

If the application is refused in whole or in part, I request that you:
(a) state the reasons for refusal, citing the specific exception(s) under \
Article 4 of Regulation 1049/2001;
(b) inform me of my right to make a confirmatory application under \
Article 7(2); and
(c) release any parts of the documents that are not covered by an exception, \
in accordance with Article 4(6) (partial access).

IDENTITY: Article 6(1) requires the applicant to be identified. My details \
are provided below.

{% if additional_notes %}
Additional remarks: {{ additional_notes }}
{% endif %}

I look forward to your timely response.

Yours faithfully,

{{ requester_name }}
{% if requester_org %}{{ requester_org }}{% endif %}
{% if requester_address %}{{ requester_address }}{% endif %}
{% if requester_email %}{{ requester_email }}{% endif %}
{% if requester_phone %}{{ requester_phone }}{% endif %}
"""


class EURequestGenerator(RequestGenerator):
    """Generate access-to-documents requests under EU Regulation 1049/2001."""

    def __init__(self) -> None:
        super().__init__()

    def generate(self, context: RequestContext, aarhus: bool = True) -> GeneratedRequest:
        inst_key = self._resolve_institution(context.agency)
        inst_info = EU_INSTITUTIONS.get(inst_key)
        if inst_info is None:
            raise ValueError(
                f"Unknown institution '{context.agency}'. Known: "
                f"{', '.join(EU_INSTITUTIONS.keys())}"
            )

        text = self._render(
            EU_REQUEST_TEMPLATE,
            context,
            agency_full_name=inst_info["full_name"],
            agency_address=inst_info["address"],
            agency_email=inst_info.get("email", ""),
            aarhus=aarhus,
        )

        return GeneratedRequest(
            text=text.strip(),
            jurisdiction="EU",
            agency=inst_info["full_name"],
            legal_basis=(
                "Regulation (EC) No 1049/2001 of 30 May 2001 regarding public access "
                "to EP, Council and Commission documents; Regulation (EC) No 1367/2006 "
                "(Aarhus Regulation) for environmental information"
            ),
            estimated_deadline_days=15,
            filing_method="email or online portal",
            fee_notes=(
                "No application fee. Charges may apply only for very large volumes "
                "of paper copies. Electronic access is free."
            ),
            context=context,
            metadata={
                "institution_key": inst_key,
                "institution_email": inst_info.get("email", ""),
                "institution_portal": inst_info.get("portal", ""),
                "aarhus_included": aarhus,
            },
        )

    def get_agencies(self) -> dict[str, dict[str, str]]:
        return EU_INSTITUTIONS

    def get_legal_basis(self) -> str:
        return (
            "Regulation (EC) No 1049/2001 of the European Parliament and of the "
            "Council of 30 May 2001. Article 2: any citizen or resident of the EU "
            "has a right of access. Article 4: exceptions (limited and to be "
            "interpreted narrowly). Article 7: 15 working days deadline. "
            "Regulation (EC) No 1367/2006 (Aarhus) applies an overriding public "
            "interest test for environmental information."
        )

    def get_fee_waiver_language(self, context: RequestContext) -> str:
        return (
            "Access to documents of EU institutions is free of charge. "
            "Article 10(1) of Regulation 1049/2001 provides that access by "
            "consultation on the spot, by electronic copies, or by copies of "
            "fewer than 20 A4 pages shall be free."
        )

    def get_appeal_info(self) -> dict[str, str]:
        return {
            "confirmatory_application": (
                "Under Article 7(2) of Regulation 1049/2001, within 15 working "
                "days of receiving a total or partial refusal, the applicant may "
                "make a confirmatory application asking the institution to "
                "reconsider. The institution must respond within 15 working "
                "days (extendable by 15 more)."
            ),
            "ombudsman": (
                "If the confirmatory application is refused, the applicant may "
                "complain to the European Ombudsman under Article 228 TFEU. "
                "Contact: https://www.ombudsman.europa.eu/"
            ),
            "court": (
                "Alternatively, the applicant may bring an action before the "
                "General Court (formerly Court of First Instance) under "
                "Article 263 TFEU, within two months of the refusal."
            ),
        }

    @staticmethod
    def _resolve_institution(raw: str) -> str:
        upper = raw.upper().strip()
        if upper in EU_INSTITUTIONS:
            return upper
        aliases: dict[str, str] = {
            "DG SANTE": "EC-DG-SANTE",
            "SANTE": "EC-DG-SANTE",
            "DG AGRI": "EC-DG-AGRI",
            "AGRI": "EC-DG-AGRI",
            "DG ENV": "EC-DG-ENV",
            "ENVIRONMENT": "EC-DG-ENV",
            "EFSA": "EFSA",
            "FOOD SAFETY AUTHORITY": "EFSA",
            "COURT OF AUDITORS": "ECA",
            "COUNCIL": "EU-COUNCIL",
            "PARLIAMENT": "EU-PARLIAMENT",
        }
        for alias, key in aliases.items():
            if alias in upper:
                return key
        return raw
