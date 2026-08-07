from __future__ import annotations

VALID_PHASES = {"free", "reserved", "locked"}

TRANSITIONS: dict[tuple[str, str], str] = {
    ("free", "pod_start"): "locked",
    ("free", "personnel_req"): "reserved",
    ("locked", "pod_done_nil"): "free",
    ("locked", "pod_done_set"): "reserved",
    ("reserved", "personnel_clr"): "free",
}


def transition(current_phase: str, event: str) -> str | None:
    return TRANSITIONS.get((current_phase, event))


def is_valid_transition(current_phase: str, desired_phase: str) -> bool:
    if current_phase == desired_phase:
        return False
    if current_phase == "reserved" and desired_phase == "locked":
        return False
    if current_phase == "locked" and desired_phase == "locked":
        return False
    if current_phase == "reserved" and desired_phase == "reserved":
        return False
    return True
