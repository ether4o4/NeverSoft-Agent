"""Build Completion Loop policy and phase model."""

from __future__ import annotations

from enum import StrEnum


class BuildPhase(StrEnum):
    RECEIVED = "received"
    INSPECT = "inspect"
    IMPLEMENT = "implement"
    BUILD = "build"
    TEST = "test"
    RECOVER = "recover"
    AUDIT = "audit"
    VERIFY = "verify"
    COMPLETE = "complete"
    BLOCKED = "blocked"


COMPLETION_RULES = (
    "Inspect the whole project before declaring it complete.",
    "Implement missing necessary behavior, not merely requested surface features.",
    "Run the strongest available build and test commands.",
    "Treat every failure as input to another recovery iteration.",
    "Audit navigation, state, validation, errors, loading, empty states, accessibility, and platform requirements.",
    "Verify the expected artifact exists and is structurally valid before completion.",
    "Add a small number of useful luxury improvements that reinforce the core product.",
    "Never report completion without evidence.",
)
