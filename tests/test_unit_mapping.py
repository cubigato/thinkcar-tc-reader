"""Tests for known parameter-unit fallbacks."""

import pytest

from thinkcar_tc_reader.unit_mapping import (
    KNOWN_PARAMETER_UNITS,
    apply_known_unit_fallbacks,
)


def test_known_mapping_contains_observed_units():
    assert KNOWN_PARAMETER_UNITS["Engine Speed"] == ("rpm",)
    assert KNOWN_PARAMETER_UNITS["Engine Coolant Temperature"] == ("degree C",)
    assert KNOWN_PARAMETER_UNITS["Front Wheel Speed"] == ("km/h", "rpm")


def test_fallback_fills_missing_units_and_preserves_embedded_units():
    result = apply_known_unit_fallbacks(
        ["Engine Speed", "Comp Power Supply Voltage"],
        ["1/min", ""],
    )

    assert result == ["1/min", "V"]


def test_fallback_resolves_duplicate_names_by_occurrence():
    result = apply_known_unit_fallbacks(
        ["Front Wheel Speed", "Front Wheel Speed"],
        ["", ""],
    )

    assert result == ["km/h", "rpm"]


def test_fallback_leaves_unknown_parameter_empty():
    assert apply_known_unit_fallbacks(["Unknown"], [""]) == [""]


def test_fallback_rejects_mismatched_lists():
    with pytest.raises(ValueError, match="same length"):
        apply_known_unit_fallbacks(["Engine Speed"], [])
