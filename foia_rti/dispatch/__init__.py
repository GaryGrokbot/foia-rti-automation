"""
Dispatch layer for coordinating multi-persona FOIA/RTI filing campaigns.

Connects persona Gmail accounts to request templates, handling rate
limiting, jurisdiction matching, and dispatch reporting.
"""

from foia_rti.dispatch.config import (
    PersonaAccount,
    DispatchTarget,
    DispatchConfig,
    load_dispatch_config,
)
from foia_rti.dispatch.runner import DispatchRunner

__all__ = [
    "PersonaAccount",
    "DispatchTarget",
    "DispatchConfig",
    "DispatchRunner",
    "load_dispatch_config",
]
