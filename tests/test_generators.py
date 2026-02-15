"""
Tests for FOIA/RTI request generators.
"""

from datetime import date

import pytest

from foia_rti.generators.generator_base import RequestContext, GeneratedRequest
from foia_rti.generators.us_federal import USFederalGenerator, US_FEDERAL_AGENCIES
from foia_rti.generators.us_state import USStateGenerator, STATE_REGISTRY
from foia_rti.generators.india_rti import IndiaRTIGenerator, INDIA_AGENCIES
from foia_rti.generators.uk_foi import UKFOIGenerator, UK_AGENCIES
from foia_rti.generators.eu_requests import EURequestGenerator, EU_INSTITUTIONS
from foia_rti.tracker.deadlines import DeadlineCalculator, add_business_days, add_calendar_days
from foia_rti.tracker.tracker import TrackerDB, FOIARequest, RequestStatus
from foia_rti.analysis.response_parser import ResponseParser
from foia_rti.analysis.redaction_detector import RedactionDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(
    agency: str = "USDA-APHIS",
    topic: str = "Animal Welfare Act inspection reports",
    jurisdiction: str = "US-Federal",
    **kwargs,
) -> RequestContext:
    defaults = dict(
        agency=agency,
        topic=topic,
        jurisdiction=jurisdiction,
        requester_name="Test Requester",
        requester_organization="Test Org",
        requester_email="test@example.org",
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2025, 12, 31),
        specific_records=["All inspection reports for licensed facilities"],
        keywords=["AWA", "inspection"],
    )
    defaults.update(kwargs)
    return RequestContext(**defaults)


# ---------------------------------------------------------------------------
# US Federal Generator
# ---------------------------------------------------------------------------

class TestUSFederalGenerator:
    def setup_method(self):
        self.gen = USFederalGenerator()

    def test_generate_basic_request(self):
        ctx = _make_context()
        result = self.gen.generate(ctx)
        assert isinstance(result, GeneratedRequest)
        assert result.jurisdiction == "US-Federal"
        assert "5 U.S.C." in result.legal_basis
        assert result.estimated_deadline_days == 20

    def test_request_contains_legal_citation(self):
        ctx = _make_context()
        result = self.gen.generate(ctx)
        assert "5 U.S.C. \u00a7 552" in result.text

    def test_request_contains_agency_name(self):
        ctx = _make_context(agency="EPA")
        result = self.gen.generate(ctx)
        assert "Environmental Protection Agency" in result.text

    def test_request_contains_fee_waiver(self):
        ctx = _make_context(fee_waiver=True)
        result = self.gen.generate(ctx)
        assert "fee waiver" in result.text.lower() or "FEE WAIVER" in result.text

    def test_request_without_fee_waiver(self):
        ctx = _make_context(fee_waiver=False)
        result = self.gen.generate(ctx)
        # Fee waiver section should not appear
        assert "FEE WAIVER REQUEST" not in result.text

    def test_request_contains_date_range(self):
        ctx = _make_context()
        result = self.gen.generate(ctx)
        assert "January 01, 2024" in result.text
        assert "December 31, 2025" in result.text

    def test_request_contains_specific_records(self):
        ctx = _make_context(specific_records=["Record type A", "Record type B"])
        result = self.gen.generate(ctx)
        assert "Record type A" in result.text
        assert "Record type B" in result.text

    def test_request_contains_keywords(self):
        ctx = _make_context(keywords=["ammonia", "CAFO", "discharge"])
        result = self.gen.generate(ctx)
        assert "ammonia" in result.text
        assert "CAFO" in result.text

    def test_request_expedited_processing(self):
        ctx = _make_context(expedited_processing=True)
        result = self.gen.generate(ctx)
        assert "expedited processing" in result.text.lower()

    def test_unknown_agency_raises(self):
        ctx = _make_context(agency="NONEXISTENT_AGENCY_XYZ")
        with pytest.raises(ValueError, match="Unknown agency"):
            self.gen.generate(ctx)

    def test_agency_aliases(self):
        for alias in ["USDA", "APHIS", "FSIS", "EPA", "FDA", "OSHA"]:
            ctx = _make_context(agency=alias)
            result = self.gen.generate(ctx)
            assert isinstance(result, GeneratedRequest)

    def test_all_agencies_registered(self):
        expected = ["USDA-APHIS", "USDA-FSIS", "USDA-AMS", "USDA-FSA", "EPA", "FDA", "OSHA", "USDA-NRCS"]
        for agency_key in expected:
            assert agency_key in US_FEDERAL_AGENCIES

    def test_get_agencies(self):
        agencies = self.gen.get_agencies()
        assert len(agencies) >= 8
        assert "USDA-APHIS" in agencies

    def test_get_legal_basis(self):
        basis = self.gen.get_legal_basis()
        assert "5 U.S.C." in basis

    def test_get_appeal_info(self):
        info = self.gen.get_appeal_info()
        assert "ogis" in info
        assert "OGIS" in info["ogis"] or "ogis" in info["ogis"]

    def test_template_loading(self):
        templates = self.gen.list_templates()
        assert len(templates) >= 20

    def test_generate_with_template(self):
        ctx = _make_context(template_id="usda-aphis-inspection-reports")
        result = self.gen.generate(ctx)
        assert "inspection" in result.text.lower()

    def test_metadata_includes_email(self):
        ctx = _make_context(agency="EPA")
        result = self.gen.generate(ctx)
        assert "agency_email" in result.metadata
        assert "@" in result.metadata["agency_email"]


# ---------------------------------------------------------------------------
# US State Generator
# ---------------------------------------------------------------------------

class TestUSStateGenerator:
    def setup_method(self):
        self.gen = USStateGenerator()

    def test_generate_iowa_request(self):
        ctx = _make_context(
            agency="Iowa DNR",
            jurisdiction="IA",
        )
        result = self.gen.generate(ctx)
        assert "Iowa Code Chapter 22" in result.text
        assert result.jurisdiction == "US-State-IA"

    def test_generate_texas_request(self):
        ctx = _make_context(
            agency="TCEQ",
            jurisdiction="TX",
        )
        result = self.gen.generate(ctx)
        assert "Tex. Gov" in result.text or "Texas" in result.text

    def test_generate_california_request(self):
        ctx = _make_context(
            agency="CDFA",
            jurisdiction="CA",
        )
        result = self.gen.generate(ctx)
        assert "Cal. Gov" in result.text or "California" in result.text

    def test_all_states_have_agencies(self):
        for abbr, info in STATE_REGISTRY.items():
            assert len(info.key_agencies) >= 1, f"State {abbr} has no agencies"

    def test_supported_states_count(self):
        states = self.gen.get_supported_states()
        assert len(states) >= 10

    def test_unknown_state_raises(self):
        ctx = _make_context(agency="Test", jurisdiction="ZZ")
        with pytest.raises(ValueError, match="Unknown state"):
            self.gen.generate(ctx)

    def test_full_state_name_resolution(self):
        ctx = _make_context(agency="Iowa DNR", jurisdiction="Iowa")
        result = self.gen.generate(ctx)
        assert "Iowa" in result.text


# ---------------------------------------------------------------------------
# India RTI Generator
# ---------------------------------------------------------------------------

class TestIndiaRTIGenerator:
    def setup_method(self):
        self.gen = IndiaRTIGenerator()

    def test_generate_english_request(self):
        ctx = _make_context(
            agency="AWBI",
            jurisdiction="India",
            topic="Slaughterhouse inspections in Tamil Nadu",
        )
        result = self.gen.generate(ctx, language="english")
        assert "Right to Information Act" in result.text
        assert "Section 6" in result.text
        assert result.estimated_deadline_days == 30

    def test_generate_hindi_request(self):
        ctx = _make_context(
            agency="AWBI",
            jurisdiction="India",
            topic="Slaughterhouse inspections",
        )
        result = self.gen.generate(ctx, language="hindi")
        # Should contain Hindi text
        assert "सूचना का अधिकार" in result.text

    def test_fee_note_present(self):
        ctx = _make_context(agency="FSSAI", jurisdiction="India")
        result = self.gen.generate(ctx, language="english")
        assert "Rs. 10" in result.text

    def test_all_agencies_registered(self):
        expected = ["AWBI", "FSSAI", "CPCB", "DAHD", "MoEFCC"]
        for key in expected:
            assert key in INDIA_AGENCIES

    def test_template_loading(self):
        templates = self.gen.list_templates()
        assert len(templates) >= 10

    def test_bpl_exemption(self):
        ctx = _make_context(agency="AWBI", jurisdiction="India")
        result = self.gen.generate(ctx, bpl=True)
        assert "Below Poverty Line" in result.text or "BPL" in result.text


# ---------------------------------------------------------------------------
# UK FOI Generator
# ---------------------------------------------------------------------------

class TestUKFOIGenerator:
    def setup_method(self):
        self.gen = UKFOIGenerator()

    def test_generate_defra_request(self):
        ctx = _make_context(
            agency="DEFRA",
            jurisdiction="UK",
            topic="Farm inspection reports",
        )
        result = self.gen.generate(ctx)
        assert "Freedom of Information Act 2000" in result.text
        assert result.estimated_deadline_days == 20

    def test_eir_included_by_default(self):
        ctx = _make_context(agency="EA", jurisdiction="UK")
        result = self.gen.generate(ctx)
        assert "Environmental Information Regulations" in result.text

    def test_eir_excluded(self):
        ctx = _make_context(agency="FSA", jurisdiction="UK")
        result = self.gen.generate(ctx, eir=False)
        assert "Environmental Information Regulations" not in result.text

    def test_all_agencies_registered(self):
        expected = ["DEFRA", "FSA", "EA", "APHA", "VMD"]
        for key in expected:
            assert key in UK_AGENCIES


# ---------------------------------------------------------------------------
# EU Request Generator
# ---------------------------------------------------------------------------

class TestEURequestGenerator:
    def setup_method(self):
        self.gen = EURequestGenerator()

    def test_generate_dg_sante_request(self):
        ctx = _make_context(
            agency="EC-DG-SANTE",
            jurisdiction="EU",
            topic="Animal welfare audit reports",
        )
        result = self.gen.generate(ctx)
        assert "1049/2001" in result.text
        assert result.estimated_deadline_days == 15

    def test_aarhus_included_by_default(self):
        ctx = _make_context(agency="EFSA", jurisdiction="EU")
        result = self.gen.generate(ctx)
        assert "1367/2006" in result.text or "Aarhus" in result.text

    def test_all_institutions_registered(self):
        expected = ["EC-DG-SANTE", "EC-DG-AGRI", "EC-DG-ENV", "EFSA", "ECA"]
        for key in expected:
            assert key in EU_INSTITUTIONS


# ---------------------------------------------------------------------------
# Deadline Calculator
# ---------------------------------------------------------------------------

class TestDeadlineCalculator:
    def setup_method(self):
        self.calc = DeadlineCalculator()

    def test_us_federal_20_business_days(self):
        # Monday Feb 3, 2025 + 20 biz days = Monday Mar 3, 2025
        filed = date(2025, 2, 3)
        deadline = self.calc.calculate("US-Federal", filed)
        assert deadline.weekday() < 5  # Should be a weekday
        # Approximately 4 weeks of business days
        delta = (deadline - filed).days
        assert 25 <= delta <= 32  # 20 business days is ~28 calendar days

    def test_india_30_calendar_days(self):
        filed = date(2025, 2, 1)
        deadline = self.calc.calculate("India", filed)
        assert deadline == date(2025, 3, 3)

    def test_uk_20_working_days(self):
        filed = date(2025, 2, 3)
        deadline = self.calc.calculate("UK", filed)
        delta = (deadline - filed).days
        assert 25 <= delta <= 32

    def test_eu_15_working_days(self):
        filed = date(2025, 2, 3)
        deadline = self.calc.calculate("EU", filed)
        delta = (deadline - filed).days
        assert 18 <= delta <= 25

    def test_extension_us_federal(self):
        filed = date(2025, 2, 3)
        initial = self.calc.calculate("US-Federal", filed)
        extended = self.calc.calculate_extension("US-Federal", initial)
        assert extended is not None
        assert extended > initial

    def test_extension_india_none(self):
        filed = date(2025, 2, 1)
        initial = self.calc.calculate("India", filed)
        extended = self.calc.calculate_extension("India", initial)
        assert extended is None

    def test_add_business_days_skips_weekend(self):
        # Friday + 1 business day = Monday
        friday = date(2025, 2, 7)
        result = add_business_days(friday, 1)
        assert result == date(2025, 2, 10)
        assert result.weekday() == 0  # Monday

    def test_add_calendar_days(self):
        start = date(2025, 2, 1)
        result = add_calendar_days(start, 30)
        assert result == date(2025, 3, 3)

    def test_unknown_jurisdiction_raises(self):
        with pytest.raises(ValueError, match="No deadline rules"):
            self.calc.calculate("Atlantis", date(2025, 1, 1))

    def test_list_jurisdictions(self):
        jurisdictions = self.calc.list_jurisdictions()
        assert "US-Federal" in jurisdictions
        assert "India" in jurisdictions
        assert "UK" in jurisdictions
        assert "EU" in jurisdictions


# ---------------------------------------------------------------------------
# Tracker DB (in-memory SQLite)
# ---------------------------------------------------------------------------

class TestTrackerDB:
    def setup_method(self):
        self.db = TrackerDB("sqlite:///:memory:")

    def test_create_and_retrieve(self):
        req = self.db.create_request(
            agency="USDA-APHIS",
            jurisdiction="US-Federal",
            topic="Inspection reports",
        )
        assert req.id is not None
        retrieved = self.db.get_request(req.id)
        assert retrieved is not None
        assert retrieved.agency == "USDA-APHIS"

    def test_update_status(self):
        req = self.db.create_request(
            agency="EPA",
            jurisdiction="US-Federal",
            topic="CAFO permits",
        )
        updated = self.db.update_status(req.id, RequestStatus.FILED, date_filed=date.today())
        assert updated.status == RequestStatus.FILED

    def test_list_requests(self):
        self.db.create_request(agency="A", jurisdiction="US-Federal", topic="T1")
        self.db.create_request(agency="B", jurisdiction="India", topic="T2")
        all_reqs = self.db.list_requests()
        assert len(all_reqs) == 2
        us_reqs = self.db.list_requests(jurisdiction="US-Federal")
        assert len(us_reqs) == 1

    def test_add_note(self):
        req = self.db.create_request(agency="A", jurisdiction="UK", topic="T")
        self.db.add_note(req.id, "First note")
        self.db.add_note(req.id, "Second note")
        updated = self.db.get_request(req.id)
        assert "First note" in updated.notes
        assert "Second note" in updated.notes

    def test_record_response(self):
        req = self.db.create_request(agency="A", jurisdiction="EU", topic="T")
        self.db.record_response(
            req.id,
            docs_received=5,
            pages_received=100,
            pages_withheld=20,
            exemptions_cited="(b)(4), (b)(6)",
        )
        updated = self.db.get_request(req.id)
        assert updated.docs_received == 5
        assert updated.pages_withheld == 20
        assert updated.status == RequestStatus.PARTIAL_RESPONSE

    def test_delete_request(self):
        req = self.db.create_request(agency="A", jurisdiction="US-Federal", topic="T")
        assert self.db.delete_request(req.id) is True
        assert self.db.get_request(req.id) is None

    def test_get_stats(self):
        self.db.create_request(agency="A", jurisdiction="US-Federal", topic="T1")
        self.db.create_request(agency="B", jurisdiction="India", topic="T2")
        stats = self.db.get_stats()
        assert stats["total"] == 2

    def test_overdue_detection(self):
        req = self.db.create_request(
            agency="A",
            jurisdiction="US-Federal",
            topic="T",
            date_filed=date(2024, 1, 1),
            deadline=date(2024, 2, 1),
            status=RequestStatus.FILED,
        )
        overdue = self.db.get_overdue()
        assert len(overdue) >= 1
        assert overdue[0].id == req.id


# ---------------------------------------------------------------------------
# Response Parser
# ---------------------------------------------------------------------------

class TestResponseParser:
    def setup_method(self):
        self.parser = ResponseParser()

    def test_detect_full_grant(self):
        text = "We are granting your request in full. 150 pages released."
        result = self.parser.parse(text, "US-Federal")
        assert result.determination == "full_grant"

    def test_detect_partial_grant(self):
        text = "Your request is granted in part. 100 pages released. 50 pages withheld under (b)(4)."
        result = self.parser.parse(text, "US-Federal")
        assert result.determination == "partial_grant"

    def test_detect_denial(self):
        text = "Your request is denied pursuant to Exemption (b)(7)(A)."
        result = self.parser.parse(text, "US-Federal")
        assert result.determination == "denial"

    def test_detect_no_records(self):
        text = "A thorough search was conducted. No responsive records were located."
        result = self.parser.parse(text, "US-Federal")
        assert result.determination == "no_records"

    def test_extract_us_exemptions(self):
        text = "Portions withheld under (b)(4) and (b)(6). Also (b)(7)(C) applied."
        result = self.parser.parse(text, "US-Federal")
        assert "(b)(4)" in result.exemptions
        assert "(b)(6)" in result.exemptions
        assert "(b)(7)(C)" in result.exemptions

    def test_extract_page_counts(self):
        text = "We are releasing 250 pages. 75 pages were withheld in full."
        result = self.parser.parse(text, "US-Federal")
        assert result.pages_released == 250
        assert result.pages_withheld_full == 75

    def test_extract_tracking_number(self):
        text = "Your request has been assigned tracking number FOIA-2026-00345."
        result = self.parser.parse(text, "US-Federal")
        assert "FOIA-2026-00345" in result.tracking_number

    def test_detect_fee_waiver_granted(self):
        text = "Your fee waiver request has been granted."
        result = self.parser.parse(text, "US-Federal")
        assert result.fee_waiver_granted is True

    def test_detect_fee_waiver_denied(self):
        text = "Your fee waiver request has been denied."
        result = self.parser.parse(text, "US-Federal")
        assert result.fee_waiver_granted is False

    def test_extract_uk_exemptions(self):
        text = "Information withheld under Section 43 (commercial interests) and Section 40 (personal data)."
        result = self.parser.parse(text, "UK")
        assert any("43" in e for e in result.exemptions)
        assert any("40" in e for e in result.exemptions)

    def test_extract_india_exemptions(self):
        text = "Information denied under Section 8(1)(d) of the RTI Act."
        result = self.parser.parse(text, "India")
        assert any("8(1)(d)" in e for e in result.exemptions)


# ---------------------------------------------------------------------------
# Redaction Detector
# ---------------------------------------------------------------------------

class TestRedactionDetector:
    def setup_method(self):
        self.detector = RedactionDetector()
        self.parser = ResponseParser()

    def test_flag_excessive_withholding(self):
        text = "We are releasing 20 pages. 180 pages were withheld under (b)(4)."
        parsed = self.parser.parse(text, "US-Federal")
        report = self.detector.analyze(parsed, "US-Federal")
        assert any(f.category == "Excessive Withholding" for f in report.flags)
        assert report.appeal_recommended

    def test_flag_blanket_denial(self):
        text = "Your request is denied under (b)(5). No records are released."
        parsed = self.parser.parse(text, "US-Federal")
        # Manually set pages to simulate full denial
        parsed.pages_released = 0
        parsed.pages_withheld_full = 100
        report = self.detector.analyze(parsed, "US-Federal")
        assert any(f.category == "Blanket Denial" for f in report.flags)

    def test_flag_b5_overuse(self):
        text = "Information withheld under (b)(5) deliberative process. 50 pages released. 30 pages withheld."
        parsed = self.parser.parse(text, "US-Federal")
        report = self.detector.analyze(parsed, "US-Federal")
        assert any("Exemption 5" in f.category or "(b)(5)" in (f.exemption or "") for f in report.flags)

    def test_no_flags_for_clean_response(self):
        text = "Granting your request in full. 100 pages released. No pages withheld."
        parsed = self.parser.parse(text, "US-Federal")
        report = self.detector.analyze(parsed, "US-Federal")
        assert len(report.flags) == 0
        assert not report.appeal_recommended

    def test_risk_score_calculation(self):
        text = "Denied under (b)(4), (b)(5), (b)(6), (b)(7)(C). 0 pages released. 500 pages withheld."
        parsed = self.parser.parse(text, "US-Federal")
        report = self.detector.analyze(parsed, "US-Federal")
        assert report.risk_score > 0.5

    def test_format_report(self):
        text = "Denied. 200 pages withheld under (b)(5). 10 pages released."
        parsed = self.parser.parse(text, "US-Federal")
        report = self.detector.analyze(parsed, "US-Federal")
        formatted = report.format_report()
        assert "REDACTION ANALYSIS REPORT" in formatted
        assert "Risk Score" in formatted


# ---------------------------------------------------------------------------
# Request Context
# ---------------------------------------------------------------------------

class TestRequestContext:
    def test_date_range_str_both(self):
        ctx = _make_context()
        assert "January 01, 2024" in ctx.date_range_str
        assert "December 31, 2025" in ctx.date_range_str

    def test_date_range_str_start_only(self):
        ctx = _make_context(date_range_start=date(2024, 6, 1), date_range_end=None)
        assert "June 01, 2024" in ctx.date_range_str
        assert "present" in ctx.date_range_str

    def test_date_range_str_none(self):
        ctx = _make_context(date_range_start=None, date_range_end=None)
        assert "all available" in ctx.date_range_str

    def test_filing_date(self):
        ctx = _make_context()
        assert len(ctx.filing_date) > 0
