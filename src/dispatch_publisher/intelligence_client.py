"""
Intelligence integration boundary — mirrors library_client.py's posture.

Publisher consumes `PublisherRequirement` objects produced by
`dispatch_intel.service.route_to_publisher()` (Intelligence repo). Since the repos share no
package dependency, this module defines the minimal duck-typed shape Publisher needs
(`requirement_id`, `requirement_type`, `status`, `mandatory`) rather than importing the
Intelligence repo's dataclass directly. Field names match
DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md Section 3.4 exactly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Protocol


class SupportsPublisherRequirement(Protocol):
    requirement_id: str
    requirement_type: str
    status: str
    mandatory: bool


def requirement_types_present(
    requirements: List[Any], required_types: List[str]
) -> Dict[str, bool]:
    """For each required Intelligence-requirement type, is a READY requirement of that type present?

    Never fabricates presence: a required_type with no matching, READY requirement in
    `requirements` is reported False (i.e. MISSING), not silently dropped.
    """
    ready_types = {
        getattr(r, "requirement_type", None)
        for r in requirements
        if getattr(r, "status", None) == "READY"
    }
    return {rt: rt in ready_types for rt in required_types}
