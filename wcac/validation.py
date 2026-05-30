"""
wcac.validation — input validation for WCAC calculations.

The core solver intentionally computes whatever it is given (matching the
spreadsheet, which also does no input guarding). This module provides a
SHARED validation layer that every front-end (CLI, web, desktop, API) can
call so they all enforce the same physical and correlation-range limits.

Findings that motivated each check are documented in
tests/reference_data/validation_cases.py, where each limit is cited to the
VBA source comments or basic physics.

Usage::

    from wcac import validate, WCACInputs
    issues = validate(WCACInputs(shell_temp_in_F=-5))
    for issue in issues:
        print(issue.severity, issue.field, issue.message)

    # or fail-fast:
    from wcac import calculate
    result = calculate(inputs, validate_inputs=True)  # raises on ERROR
"""
from dataclasses import dataclass
from enum import Enum
from typing import List


class Severity(Enum):
    ERROR   = 'error'    # physically impossible / will produce garbage → reject
    WARNING = 'warning'  # outside correlation fit range → result unreliable


@dataclass
class ValidationIssue:
    severity: Severity
    field:    str
    message:  str
    value:    object = None


class WCACValidationError(ValueError):
    """Raised by calculate(validate_inputs=True) when an ERROR-level issue exists."""
    def __init__(self, issues):
        self.issues = issues
        msg = '; '.join(f'{i.field}: {i.message}' for i in issues
                        if i.severity is Severity.ERROR)
        super().__init__(msg)


# ── Fluid property validity ranges (°C), from VBA source comments ─────────────
_FLUID_RANGE_C = {
    'Air':                    (-100, 425),
    'Argon':                  (0, 1200),
    'Carbon dioxide':         (0, 1200),
    'Carbon monoxide':        (0, 1200),
    'Helium':                 (-150, 1200),
    'Hydrogen':               (0, 1200),
    'Methane':                (0, 1200),
    'Nitrogen':               (0, 1200),
    'Oxygen':                 (0, 1200),
    'Water':                  (0.01, 300),
    'Sea water':              (10, 120),
    'Water/ethylene glycol':  (None, 125),   # lower depends on concentration
    'Water/propylene glycol': (None, 120),
}

VALID_MODELS = None  # filled lazily from wcac.models


def _f_to_c(f):
    return (f - 32.0) / 1.8


def validate(inp) -> List[ValidationIssue]:
    """Return a list of ValidationIssue for the given WCACInputs.

    An empty list means all checks passed. ERROR issues mean the result would
    be physically meaningless; WARNING issues mean a correlation is used outside
    its fitted range (result plausible but not guaranteed).
    """
    global VALID_MODELS
    issues: List[ValidationIssue] = []

    def err(field, msg, value=None):
        issues.append(ValidationIssue(Severity.ERROR, field, msg, value))
    def warn(field, msg, value=None):
        issues.append(ValidationIssue(Severity.WARNING, field, msg, value))

    # ── Model in catalogue ───────────────────────────────────────────────
    if VALID_MODELS is None:
        from .models import list_models
        VALID_MODELS = set(list_models())
    if inp.model not in VALID_MODELS:
        err('model', f"unknown model '{inp.model}' (valid: W0035-W5000)", inp.model)

    # ── Flows: positive and non-zero ─────────────────────────────────────
    if inp.tube_flow <= 0:
        err('tube_flow', 'tube-side flow must be > 0', inp.tube_flow)
    if inp.shell_flow <= 0:
        err('shell_flow', 'shell-side flow must be > 0', inp.shell_flow)

    # ── Pressures: positive absolute ──────────────────────────────────────
    if inp.tube_pressure_psig + 14.696 <= 0:
        err('tube_pressure_psig',
            f'absolute pressure must be > 0 ({inp.tube_pressure_psig} psig = '
            f'{inp.tube_pressure_psig + 14.696:.1f} psia)', inp.tube_pressure_psig)
    if inp.suction_pressure_psia <= 0:
        err('suction_pressure_psia', 'suction pressure must be > 0',
            inp.suction_pressure_psia)

    # ── Relative humidity 0-100 ───────────────────────────────────────────
    if not (0 <= inp.suction_rh_pct <= 100):
        err('suction_rh_pct', 'relative humidity must be 0-100%', inp.suction_rh_pct)

    # ── Fouling non-negative ──────────────────────────────────────────────
    if inp.tube_fouling < 0:
        err('tube_fouling', 'fouling resistance cannot be negative', inp.tube_fouling)
    if inp.shell_fouling < 0:
        err('shell_fouling', 'fouling resistance cannot be negative', inp.shell_fouling)

    # ── Surface area margin sane (< 100%) ─────────────────────────────────
    if inp.surface_area_margin >= 100:
        err('surface_area_margin',
            f'surface area margin {inp.surface_area_margin}% >= 100% gives '
            f'non-physical effective area', inp.surface_area_margin)
    elif inp.surface_area_margin > 50:
        warn('surface_area_margin',
             f'{inp.surface_area_margin}% is unusually high (typical 0-50%) — '
             f'check for data entry error', inp.surface_area_margin)

    # ── Glycol concentration 20-60% ───────────────────────────────────────
    if inp.shell_fluid in ('Water/ethylene glycol', 'Water/propylene glycol'):
        if not (20 <= inp.glycol_concentration <= 60):
            err('glycol_concentration',
                f'glycol concentration {inp.glycol_concentration}% outside '
                f'fitted range 20-60% vol', inp.glycol_concentration)

    # ── Tube fluid temperature range ──────────────────────────────────────
    t_tube_c = _f_to_c(inp.tube_temp_in_F)
    rng = _FLUID_RANGE_C.get(inp.tube_fluid)
    if rng:
        lo, hi = rng
        if lo is not None and t_tube_c < lo:
            warn('tube_temp_in_F',
                 f'{inp.tube_fluid} inlet {inp.tube_temp_in_F:.0f}°F '
                 f'({t_tube_c:.0f}°C) below fitted range {lo}°C — '
                 f'properties extrapolated', inp.tube_temp_in_F)
        if hi is not None and t_tube_c > hi:
            warn('tube_temp_in_F',
                 f'{inp.tube_fluid} inlet {inp.tube_temp_in_F:.0f}°F '
                 f'({t_tube_c:.0f}°C) above fitted range {hi}°C — '
                 f'properties extrapolated', inp.tube_temp_in_F)

    # ── Shell fluid temperature range ─────────────────────────────────────
    t_shell_c = _f_to_c(inp.shell_temp_in_F)
    rng = _FLUID_RANGE_C.get(inp.shell_fluid)
    if rng:
        lo, hi = rng
        if lo is not None and t_shell_c < lo:
            warn('shell_temp_in_F',
                 f'{inp.shell_fluid} inlet {inp.shell_temp_in_F:.0f}°F '
                 f'({t_shell_c:.0f}°C) below fitted range {lo}°C — '
                 f'properties extrapolated', inp.shell_temp_in_F)
        if hi is not None and t_shell_c > hi:
            warn('shell_temp_in_F',
                 f'{inp.shell_fluid} inlet {inp.shell_temp_in_F:.0f}°F '
                 f'({t_shell_c:.0f}°C) above fitted range {hi}°C — '
                 f'properties extrapolated', inp.shell_temp_in_F)

    # ── Aftercooler sanity: gas hotter than coolant ───────────────────────
    if inp.tube_temp_in_F <= inp.shell_temp_in_F:
        warn('tube_temp_in_F',
             f'gas inlet {inp.tube_temp_in_F:.0f}°F is not hotter than coolant '
             f'inlet {inp.shell_temp_in_F:.0f}°F — not a normal aftercooler '
             f'duty (little or no cooling)', inp.tube_temp_in_F)

    return issues


def assert_valid(inp):
    """Raise WCACValidationError if any ERROR-level issue exists."""
    issues = validate(inp)
    if any(i.severity is Severity.ERROR for i in issues):
        raise WCACValidationError(issues)
    return issues
