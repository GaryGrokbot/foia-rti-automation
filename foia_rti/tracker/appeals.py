"""
Auto-generate appeal letters for denied or overdue FOIA/RTI requests.

Each jurisdiction has specific appeal procedures, time limits, and
required legal citations. This module generates properly formatted
appeals ready for filing.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from foia_rti.tracker.tracker import FOIARequest, RequestStatus


# ---------------------------------------------------------------------------
# Appeal templates per jurisdiction
# ---------------------------------------------------------------------------

US_FEDERAL_APPEAL_TEMPLATE = """\
{filing_date}

{appeal_to}
{agency}

Re: Freedom of Information Act Appeal
Original Request Reference: {reference_id}
Date of Original Request: {date_filed}
Date of Adverse Determination: {date_response}

Dear FOIA Appeals Officer:

Pursuant to 5 U.S.C. Section 552(a)(6)(A), I hereby appeal the \
{determination_type} of my Freedom of Information Act request \
referenced above.

BACKGROUND:

On {date_filed}, I submitted a FOIA request to {agency} seeking records \
regarding: {topic}.

{denial_details}

GROUNDS FOR APPEAL:

{appeal_grounds}

The FOIA requires that exemptions be narrowly construed, and the burden \
of justifying non-disclosure rests with the agency. See Department of the \
Air Force v. Rose, 425 U.S. 352, 361 (1976). Agencies must disclose all \
reasonably segregable, non-exempt portions of records. 5 U.S.C. Section \
552(b) (final sentence).

{additional_arguments}

REQUESTED RELIEF:

I respectfully request that you:
1. Reverse the initial determination and release all responsive records;
2. To the extent any records are properly withheld, provide a detailed \
Vaughn index identifying each document and the specific exemption(s) \
applicable to each withholding; and
3. Release all reasonably segregable non-exempt portions of any partially \
withheld records.

I reserve the right to seek judicial review under 5 U.S.C. Section \
552(a)(4)(B) and to seek mediation through the Office of Government \
Information Services (OGIS) under 5 U.S.C. Section 552(h).

Sincerely,

{requester_name}
{requester_org}
{requester_email}
"""

INDIA_APPEAL_TEMPLATE = """\
{filing_date}

To,
The First Appellate Authority,
{agency}

Subject: First Appeal under Section 19(1) of the Right to Information Act, 2005
RTI Application Reference: {reference_id}
Date of Application: {date_filed}

Respected Sir/Madam,

I, {requester_name}, had filed an RTI application on {date_filed} \
before the Central/State Public Information Officer of {agency}, seeking \
information regarding: {topic}.

{denial_details}

Under Section 19(1) of the RTI Act, 2005, I hereby file this first appeal \
on the following grounds:

{appeal_grounds}

Under Section 7(1) of the RTI Act, the PIO is required to provide \
information within 30 days of receipt of the application. Failure to do \
so is deemed a refusal under Section 7(2).

Section 8 of the RTI Act enumerates specific and narrow exemptions from \
disclosure. The burden of proving that the exemption applies rests with \
the public authority. Even where Section 8(1) applies, information may be \
disclosed if the public interest in disclosure outweighs the harm to the \
protected interest (Section 8(2)).

REQUESTED RELIEF:

I request that the First Appellate Authority:
1. Direct the PIO to provide the requested information in full;
2. If any information is withheld, provide specific reasons citing the \
applicable clause of Section 8(1); and
3. Impose appropriate penalties under Section 20 if the PIO has failed \
to comply without reasonable cause.

I reserve the right to file a second appeal before the Central/State \
Information Commission under Section 19(3).

Yours faithfully,

{requester_name}
{requester_org}
{requester_email}

(प्रथम अपील — सूचना का अधिकार अधिनियम 2005 की धारा 19(1) के तहत)
"""

UK_APPEAL_TEMPLATE = """\
{filing_date}

{agency}

REQUEST FOR INTERNAL REVIEW
Original FOI Request Reference: {reference_id}
Date of Original Request: {date_filed}
Date of Response: {date_response}

Dear Sir or Madam,

I am writing to request an internal review of your response to my Freedom \
of Information request referenced above, in accordance with the Section 45 \
Code of Practice issued under the Freedom of Information Act 2000.

BACKGROUND:

On {date_filed}, I submitted a request under the Freedom of Information \
Act 2000 for information regarding: {topic}.

{denial_details}

GROUNDS FOR REVIEW:

{appeal_grounds}

The Freedom of Information Act 2000 creates a presumption in favour of \
disclosure. Where a qualified exemption is relied upon, Section 2(2)(b) \
requires the authority to demonstrate that the public interest in \
maintaining the exemption outweighs the public interest in disclosure. \
I submit that this balance favours disclosure in this case.

REQUESTED OUTCOME:

I request that you:
1. Conduct a full internal review of the decision;
2. Release the withheld information; and
3. Provide a revised response within 20 working days.

If I remain dissatisfied following this review, I intend to complain to \
the Information Commissioner's Office under Section 50 of the Act.

Yours faithfully,

{requester_name}
{requester_org}
{requester_email}
"""

EU_APPEAL_TEMPLATE = """\
{filing_date}

{agency}

CONFIRMATORY APPLICATION
Under Article 7(2) of Regulation (EC) No 1049/2001
Original Application Reference: {reference_id}
Date of Original Application: {date_filed}
Date of Initial Reply: {date_response}

Dear Sir or Madam,

Pursuant to Article 7(2) of Regulation (EC) No 1049/2001, I hereby submit \
a confirmatory application requesting the institution to reconsider its \
position regarding my request for access to documents referenced above.

BACKGROUND:

On {date_filed}, I submitted an application under Regulation 1049/2001 \
for documents regarding: {topic}.

{denial_details}

GROUNDS:

{appeal_grounds}

Article 4 exceptions must be interpreted narrowly, in light of the \
principle of the widest possible public access established in Article 1. \
The General Court has consistently held that the institution bears the \
burden of demonstrating that a document falls within an exception. See \
Case T-2/03 Verein fuer Konsumenteninformation v. Commission.

Where environmental information is concerned, Regulation (EC) No 1367/2006 \
(the Aarhus Regulation) requires an overriding public interest test to \
be applied.

REQUESTED RELIEF:

I request that the institution:
1. Grant full access to the requested documents;
2. If any document is withheld, provide detailed reasons citing the \
specific sub-paragraph of Article 4 relied upon; and
3. Grant partial access to any document for which full disclosure is \
refused, in accordance with Article 4(6).

Should this confirmatory application be refused, I reserve the right to \
bring proceedings before the General Court under Article 263 TFEU and/or \
to complain to the European Ombudsman under Article 228 TFEU.

Yours faithfully,

{requester_name}
{requester_org}
{requester_email}
"""


class AppealGenerator:
    """
    Generate jurisdiction-appropriate appeal letters.

    Usage:
        gen = AppealGenerator()
        text = gen.generate_appeal(request, grounds="The exemption was improperly applied.")
    """

    def generate_appeal(
        self,
        request: FOIARequest,
        grounds: str = "",
        requester_name: str = "Open Paws Research",
        requester_org: str = "Open Paws",
        requester_email: str = "",
    ) -> str:
        """Generate an appeal letter for the given request."""
        jurisdiction = request.jurisdiction

        denial_details = self._build_denial_details(request)
        appeal_grounds = grounds or self._default_grounds(request)
        additional = self._additional_arguments(request)

        common_vars = {
            "filing_date": datetime.now().strftime("%B %d, %Y"),
            "agency": request.agency,
            "reference_id": request.reference_id or f"Tracker #{request.id}",
            "date_filed": (
                request.date_filed.strftime("%B %d, %Y")
                if request.date_filed
                else "N/A"
            ),
            "date_response": (
                request.date_response.strftime("%B %d, %Y")
                if request.date_response
                else "no response received",
            ),
            "topic": request.topic,
            "denial_details": denial_details,
            "appeal_grounds": appeal_grounds,
            "additional_arguments": additional,
            "requester_name": requester_name,
            "requester_org": requester_org,
            "requester_email": requester_email,
        }

        if jurisdiction == "US-Federal" or jurisdiction.startswith("US-State"):
            common_vars["appeal_to"] = "FOIA Appeals Officer"
            common_vars["determination_type"] = self._determination_type(request)
            return US_FEDERAL_APPEAL_TEMPLATE.format(**common_vars)

        if jurisdiction == "India":
            return INDIA_APPEAL_TEMPLATE.format(**common_vars)

        if jurisdiction == "UK":
            return UK_APPEAL_TEMPLATE.format(**common_vars)

        if jurisdiction == "EU":
            return EU_APPEAL_TEMPLATE.format(**common_vars)

        # Fallback to US federal format
        common_vars["appeal_to"] = "Appeals Officer"
        common_vars["determination_type"] = "denial"
        return US_FEDERAL_APPEAL_TEMPLATE.format(**common_vars)

    def generate_appeal_for_nonresponse(
        self,
        request: FOIARequest,
        requester_name: str = "Open Paws Research",
        requester_org: str = "Open Paws",
        requester_email: str = "",
    ) -> str:
        """Generate an appeal specifically for constructive denial (no response)."""
        grounds = self._nonresponse_grounds(request)
        return self.generate_appeal(
            request,
            grounds=grounds,
            requester_name=requester_name,
            requester_org=requester_org,
            requester_email=requester_email,
        )

    # ---- internal helpers ----

    @staticmethod
    def _build_denial_details(req: FOIARequest) -> str:
        if req.status == RequestStatus.DENIED and req.exemptions_cited:
            return (
                f"The agency denied the request, citing the following "
                f"exemption(s): {req.exemptions_cited}."
            )
        if req.status == RequestStatus.PARTIAL_RESPONSE:
            withheld = req.pages_withheld or 0
            received = req.pages_received or 0
            exs = req.exemptions_cited or "not specified"
            return (
                f"The agency provided a partial response: {received} pages "
                f"released, {withheld} pages withheld. Exemptions cited: {exs}."
            )
        if req.is_overdue():
            return (
                "The agency has failed to respond within the statutory time "
                "limit, which constitutes a constructive denial."
            )
        return "The agency's response was inadequate or incomplete."

    @staticmethod
    def _determination_type(req: FOIARequest) -> str:
        if req.status == RequestStatus.DENIED:
            return "denial"
        if req.status == RequestStatus.PARTIAL_RESPONSE:
            return "partial denial"
        if req.is_overdue():
            return "constructive denial (failure to respond within statutory deadline)"
        return "adverse determination"

    @staticmethod
    def _default_grounds(req: FOIARequest) -> str:
        if req.exemptions_cited:
            return (
                f"The exemption(s) cited ({req.exemptions_cited}) were "
                "improperly applied. The records do not fall within the scope "
                "of the cited exemption(s), or the agency has failed to "
                "demonstrate the necessary harm that would result from disclosure."
            )
        if req.is_overdue():
            return (
                "The agency failed to respond within the statutory deadline. "
                "This failure constitutes a constructive denial and entitles "
                "the requester to appeal."
            )
        return (
            "The agency's response was inadequate. The request sought specific, "
            "identifiable records, and the agency has not demonstrated a diligent "
            "search or provided a sufficient justification for non-disclosure."
        )

    @staticmethod
    def _nonresponse_grounds(req: FOIARequest) -> str:
        juris = req.jurisdiction
        if juris == "US-Federal":
            return (
                "The agency has failed to comply with the 20 business day "
                "response requirement of 5 U.S.C. Section 552(a)(6)(A)(i). "
                "Under established precedent, this failure constitutes a "
                "constructive denial of the request and entitles the requester "
                "to immediately appeal. See Oglesby v. U.S. Dept. of Army, "
                "920 F.2d 57 (D.C. Cir. 1990)."
            )
        if juris == "India":
            return (
                "The PIO has failed to provide information within the 30-day "
                "period prescribed by Section 7(1) of the RTI Act, 2005. "
                "Under Section 7(2), the failure to give a decision within "
                "the prescribed period is deemed a refusal. The PIO may be "
                "liable for penalty under Section 20."
            )
        if juris == "UK":
            return (
                "The authority has failed to comply with the 20 working day "
                "time limit imposed by Section 10(1) of the Freedom of "
                "Information Act 2000. This constitutes a breach of the Act."
            )
        if juris == "EU":
            return (
                "The institution has failed to reply within the 15 working "
                "day deadline prescribed by Article 7(1) of Regulation "
                "1049/2001. Under established case law, the applicant is "
                "entitled to submit a confirmatory application."
            )
        return "The agency failed to respond within the legally required timeframe."

    @staticmethod
    def _additional_arguments(req: FOIARequest) -> str:
        if req.fee_waiver_requested and req.fee_waiver_granted is False:
            return (
                "Additionally, the denial of the fee waiver request was "
                "improper. The requester is a nonprofit organization seeking "
                "information in the public interest. The requested information "
                "will contribute significantly to public understanding of "
                "government operations."
            )
        return ""
