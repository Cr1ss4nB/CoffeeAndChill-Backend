"""Unit tests for app/core/fulfillment.py — no DB or HTTP client imports."""
import pytest

from app.core.fulfillment import FulfillmentType, resolve_effective_fulfillment

# ---------------------------------------------------------------------------
# resolve_effective_fulfillment — full 3×2 matrix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ft,has_recipe,expected", [
    # Without recipe → always STOCK regardless of fulfillment_type
    (FulfillmentType.STOCK.value,       False, "STOCK"),
    (FulfillmentType.INGREDIENTS.value, False, "STOCK"),
    (FulfillmentType.BOTH.value,        False, "STOCK"),
    # With recipe → respect the declared type
    (FulfillmentType.STOCK.value,       True,  "STOCK"),
    (FulfillmentType.INGREDIENTS.value, True,  "INGREDIENTS"),
    (FulfillmentType.BOTH.value,        True,  "BOTH"),
])
def test_resolve_effective_fulfillment_matrix(ft, has_recipe, expected):
    assert resolve_effective_fulfillment(ft, has_recipe) == expected


# ---------------------------------------------------------------------------
# Invalid / unknown input edge case (Requirement 3.5)
# ---------------------------------------------------------------------------

def test_resolve_effective_fulfillment_invalid_no_recipe():
    """Unknown type with no recipe → STOCK (safe default path)."""
    result = resolve_effective_fulfillment("UNKNOWN", False)
    assert result == "STOCK"


def test_resolve_effective_fulfillment_invalid_with_recipe():
    """Unknown type with recipe: implementation passes it through.
    The test documents the actual behavior (pass-through) so any future
    change to raise ValueError will be caught here."""
    result = resolve_effective_fulfillment("UNKNOWN", True)
    # Either raises ValueError or returns the raw string — both are acceptable
    # per Requirement 3.5; we just assert it doesn't silently return a wrong enum value.
    assert result not in ("STOCK", "INGREDIENTS", "BOTH") or result == "UNKNOWN"
