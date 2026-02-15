"""
Deadline calculator for FOIA/RTI requests across jurisdictions.

Accounts for:
- Business days vs calendar days
- Jurisdiction-specific response periods
- Extension rules
- Public holidays (major US federal holidays built-in; others configurable)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


# Major US federal holidays (fixed-date approximations + rules)
# In production, use a proper holiday calendar library.
US_FEDERAL_HOLIDAYS_FIXED = {
    (1, 1),   # New Year's Day
    (6, 19),  # Juneteenth
    (7, 4),   # Independence Day
    (11, 11), # Veterans Day
    (12, 25), # Christmas Day
}


def _is_us_federal_holiday(d: date) -> bool:
    """Check if a date falls on a US federal holiday (simplified)."""
    if (d.month, d.day) in US_FEDERAL_HOLIDAYS_FIXED:
        return True
    # MLK Day: 3rd Monday of January
    if d.month == 1 and d.weekday() == 0 and 15 <= d.day <= 21:
        return True
    # Presidents' Day: 3rd Monday of February
    if d.month == 2 and d.weekday() == 0 and 15 <= d.day <= 21:
        return True
    # Memorial Day: last Monday of May
    if d.month == 5 and d.weekday() == 0 and d.day >= 25:
        return True
    # Labor Day: 1st Monday of September
    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True
    # Columbus Day: 2nd Monday of October
    if d.month == 10 and d.weekday() == 0 and 8 <= d.day <= 14:
        return True
    # Thanksgiving: 4th Thursday of November
    if d.month == 11 and d.weekday() == 3 and 22 <= d.day <= 28:
        return True
    return False


# UK bank holidays (England & Wales, simplified fixed dates)
UK_BANK_HOLIDAYS_FIXED = {
    (1, 1),   # New Year's Day
    (12, 25), # Christmas Day
    (12, 26), # Boxing Day
}


def _is_uk_bank_holiday(d: date) -> bool:
    if (d.month, d.day) in UK_BANK_HOLIDAYS_FIXED:
        return True
    # Early May bank holiday: 1st Monday of May
    if d.month == 5 and d.weekday() == 0 and d.day <= 7:
        return True
    # Spring bank holiday: last Monday of May
    if d.month == 5 and d.weekday() == 0 and d.day >= 25:
        return True
    # Summer bank holiday: last Monday of August
    if d.month == 8 and d.weekday() == 0 and d.day >= 25:
        return True
    return False


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def add_business_days(
    start: date,
    days: int,
    holiday_fn=None,
) -> date:
    """Add N business days to a start date, skipping weekends and holidays."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if _is_weekend(current):
            continue
        if holiday_fn and holiday_fn(current):
            continue
        added += 1
    return current


def add_calendar_days(start: date, days: int) -> date:
    """Add N calendar days."""
    return start + timedelta(days=days)


# ---------------------------------------------------------------------------
# Jurisdiction deadline rules
# ---------------------------------------------------------------------------

JURISDICTION_RULES: dict[str, dict] = {
    "US-Federal": {
        "initial_days": 20,
        "day_type": "business",
        "holiday_fn": _is_us_federal_holiday,
        "extension_days": 10,
        "extension_type": "business",
        "notes": (
            "5 U.S.C. § 552(a)(6)(A)(i): 20 business days. "
            "Extension of up to 10 additional business days under "
            "§ 552(a)(6)(B)(i) for 'unusual circumstances.'"
        ),
    },
    "India": {
        "initial_days": 30,
        "day_type": "calendar",
        "holiday_fn": None,
        "extension_days": 0,
        "extension_type": "calendar",
        "notes": (
            "RTI Act Section 7(1): 30 days from receipt. "
            "If life/liberty at stake: 48 hours. "
            "Transfer to another PIO: 5 days for transfer + 30 days."
        ),
    },
    "UK": {
        "initial_days": 20,
        "day_type": "business",
        "holiday_fn": _is_uk_bank_holiday,
        "extension_days": 0,
        "extension_type": "business",
        "notes": (
            "FOIA 2000 Section 10(1): 20 working days (excludes weekends "
            "and bank holidays). No statutory extension, but the authority "
            "may need 'reasonable' additional time for public interest test "
            "under qualified exemptions (Section 10(3))."
        ),
    },
    "EU": {
        "initial_days": 15,
        "day_type": "business",
        "holiday_fn": None,  # EU institution holidays vary
        "extension_days": 15,
        "extension_type": "business",
        "notes": (
            "Regulation 1049/2001 Article 7(1): 15 working days. "
            "Extension of 15 working days under Article 7(3) "
            "'in exceptional cases' with reasons given."
        ),
    },
}


class DeadlineCalculator:
    """
    Calculate deadlines for FOIA/RTI requests.

    Usage:
        calc = DeadlineCalculator()
        deadline = calc.calculate("US-Federal", date(2026, 2, 15))
        extended = calc.calculate_extension("US-Federal", deadline)
    """

    def __init__(self, custom_rules: Optional[dict] = None) -> None:
        self.rules = dict(JURISDICTION_RULES)
        if custom_rules:
            self.rules.update(custom_rules)

    def calculate(
        self,
        jurisdiction: str,
        filed_date: date,
    ) -> date:
        """Calculate the initial response deadline."""
        rule = self._get_rule(jurisdiction)
        days = rule["initial_days"]
        if rule["day_type"] == "business":
            return add_business_days(filed_date, days, rule.get("holiday_fn"))
        return add_calendar_days(filed_date, days)

    def calculate_extension(
        self,
        jurisdiction: str,
        original_deadline: date,
    ) -> Optional[date]:
        """Calculate the extended deadline, if the jurisdiction allows extensions."""
        rule = self._get_rule(jurisdiction)
        ext_days = rule.get("extension_days", 0)
        if ext_days == 0:
            return None
        if rule["extension_type"] == "business":
            return add_business_days(original_deadline, ext_days, rule.get("holiday_fn"))
        return add_calendar_days(original_deadline, ext_days)

    def get_jurisdiction_info(self, jurisdiction: str) -> dict:
        """Return human-readable information about a jurisdiction's rules."""
        rule = self._get_rule(jurisdiction)
        return {
            "jurisdiction": jurisdiction,
            "initial_days": rule["initial_days"],
            "day_type": rule["day_type"],
            "extension_days": rule.get("extension_days", 0),
            "notes": rule.get("notes", ""),
        }

    def list_jurisdictions(self) -> list[str]:
        return list(self.rules.keys())

    def _get_rule(self, jurisdiction: str) -> dict:
        # Try direct match
        if jurisdiction in self.rules:
            return self.rules[jurisdiction]
        # Try prefix match for state-level (e.g. "US-State-IA" -> use "US-Federal" biz day logic)
        if jurisdiction.startswith("US-State"):
            # State deadlines vary; fall back to a generic 10 business day default
            return {
                "initial_days": 10,
                "day_type": "business",
                "holiday_fn": _is_us_federal_holiday,
                "extension_days": 0,
                "extension_type": "business",
                "notes": "State deadlines vary. Check state-specific rules.",
            }
        raise ValueError(
            f"No deadline rules for jurisdiction '{jurisdiction}'. "
            f"Known: {', '.join(self.rules.keys())}"
        )
