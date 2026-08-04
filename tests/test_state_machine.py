from __future__ import annotations

from lrm_operator.state_machine import (
    VALID_PHASES,
    is_valid_transition,
    transition,
)


class TestTransition:
    def test_free_to_locked(self):
        result = transition("free", "pod_start")
        assert result == "locked"

    def test_free_to_reserved(self):
        result = transition("free", "personnel_req")
        assert result == "reserved"

    def test_locked_to_free(self):
        result = transition("locked", "pod_done_nil")
        assert result == "free"

    def test_locked_to_reserved(self):
        result = transition("locked", "pod_done_set")
        assert result == "reserved"

    def test_reserved_to_free(self):
        result = transition("reserved", "personnel_clr")
        assert result == "free"

    def test_invalid_transition_returns_none(self):
        result = transition("locked", "pod_start")
        assert result is None

    def test_unknown_phase(self):
        result = transition("invalid", "pod_start")
        assert result is None


class TestIsValidTransition:
    def test_valid_transitions(self):
        assert is_valid_transition("free", "locked") is True
        assert is_valid_transition("free", "reserved") is True
        assert is_valid_transition("locked", "free") is True
        assert is_valid_transition("locked", "reserved") is True
        assert is_valid_transition("reserved", "free") is True

    def test_invalid_reserved_to_locked(self):
        assert is_valid_transition("reserved", "locked") is False

    def test_invalid_same_phase(self):
        assert is_valid_transition("free", "free") is False
        assert is_valid_transition("locked", "locked") is False
        assert is_valid_transition("reserved", "reserved") is False


class TestValidPhases:
    def test_known_phases(self):
        assert "free" in VALID_PHASES
        assert "reserved" in VALID_PHASES
        assert "locked" in VALID_PHASES

    def test_unknown_phase_not_in_set(self):
        assert "invalid" not in VALID_PHASES
