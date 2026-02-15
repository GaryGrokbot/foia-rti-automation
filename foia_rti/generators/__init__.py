"""
Request generators for multiple jurisdictions.

Each generator produces legally formatted public records requests
with correct citations, fee waiver language, and agency-specific details.
"""

from foia_rti.generators.generator_base import RequestGenerator
from foia_rti.generators.us_federal import USFederalGenerator
from foia_rti.generators.us_state import USStateGenerator
from foia_rti.generators.india_rti import IndiaRTIGenerator
from foia_rti.generators.uk_foi import UKFOIGenerator
from foia_rti.generators.eu_requests import EURequestGenerator

__all__ = [
    "RequestGenerator",
    "USFederalGenerator",
    "USStateGenerator",
    "IndiaRTIGenerator",
    "UKFOIGenerator",
    "EURequestGenerator",
]
