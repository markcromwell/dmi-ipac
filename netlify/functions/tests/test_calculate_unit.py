"""
Unit tests for the DMI-IPAC calculation engine.
No server required — imports calculate.py directly.

Reference case from formulas.md and CLAUDE.md:
  Model: W0230, Air 250°F tube side / Water 70°F shell side
  Source: W1279 DMI WCAC Design Program I0-1.xlsm (verified against spreadsheet)
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from calculate import solve

# ── Reference case inputs (CLAUDE.md §Reference Case) ───────────────────────
REF_INPUTS = {
    'model':                 'W0230',
    'bundle_type':           'Fixed',
    'tube_type':             'Std groove',
    'tube_material':         'Stainless (S3040*)',
    'tube_fluid':            'Air',
    'tube_pressure_psig':    150,
    'tube_temp_in_F':        250,
    'tube_flow':             1423,
    'tube_flow_uom':         'Scfm',
    'tube_fouling':          0,
    'shell_fluid':           'Water',
    'shell_temp_in_F':       70,
    'shell_flow':            60,
    'shell_flow_uom':        'USgpm',
    'shell_fouling':         0,
    'surface_area_margin':   0,
    'suction_pressure_psia': 14.7,
    'suction_temp_F':        85,
    'suction_rh_pct':        36,
}


@pytest.fixture(scope='module')
def ref():
    """Run the reference case once; share across all tests in this module."""
    return solve(REF_INPUTS)


# ── Reference case: verified against W1279 spreadsheet ──────────────────────

def test_total_heat_btu_h(ref):
    """Total heat transfer: 292,245 Btu/h ± 5,000 (1.7%)
    Note: our simplified single-zone condensation model gives ~1.3% lower Q than the
    spreadsheet's two-zone wet/dry model (formulas.md §12.2). This tolerance catches
    real formula bugs while accepting the known simplification.
    """
    assert abs(ref['Q_Btu_h'] - 292245) <= 5000, (
        f"Q = {ref['Q_Btu_h']:.0f} Btu/h — expected 292,245 ± 5,000"
    )

def test_tube_outlet_f(ref):
    """Tube outlet temperature: 93.6°F ± 3°F
    Note: the spreadsheet's two-zone condensation model gives slightly more heat
    transfer in the wet zone, so tube_out is ~3°F lower than our single-zone result.
    Tolerance catches wrong fluid properties, wrong model geometry, etc.
    """
    assert abs(ref['tube_out_F'] - 93.6) <= 3.0, (
        f"tube_out = {ref['tube_out_F']}°F — expected 93.6 ± 3.0"
    )

def test_shell_outlet_f(ref):
    """Shell outlet temperature: 79.8°F ± 0.5°F"""
    assert abs(ref['shell_out_F'] - 79.8) <= 0.5, (
        f"shell_out = {ref['shell_out_F']}°F — expected 79.8 ± 0.5"
    )

def test_tube_dp_psi(ref):
    """Tube-side pressure drop: 9.06 psi ± 0.5"""
    assert abs(ref['dP_tube_psi'] - 9.06) <= 0.5, (
        f"dP_tube = {ref['dP_tube_psi']} psi — expected 9.06 ± 0.5"
    )

def test_shell_dp_psi(ref):
    """Shell-side pressure drop: 7.55 psi ± 0.5"""
    assert abs(ref['dP_shell_psi'] - 7.55) <= 0.5, (
        f"dP_shell = {ref['dP_shell_psi']} psi — expected 7.55 ± 0.5"
    )

def test_lmtd_r(ref):
    """LMTD: 74.2°R ± 5°R
    Note: LMTD follows tube_out; wider tolerance matches the condensation model limitation.
    """
    assert abs(ref['LMTD_R'] - 74.2) <= 5.0, (
        f"LMTD = {ref['LMTD_R']}°R — expected 74.2 ± 5.0"
    )

def test_overall_htc(ref):
    """Overall HTC: 190 Btu/h.ft2.R ± 15
    Note: spreadsheet U = Q/(A*LMTD) includes condensation zone enhancement; our
    U is computed from component HTCs alone.
    """
    assert abs(ref['overall_U_btu'] - 190) <= 15, (
        f"U = {ref['overall_U_btu']} Btu/h.ft2.R — expected 190 ± 15"
    )

def test_surface_area_ft2(ref):
    """Surface area: 20.8 ft2 ± 0.5 — this is geometry, should be exact."""
    assert abs(ref['area_ft2'] - 20.8) <= 0.5, (
        f"area = {ref['area_ft2']} ft2 — expected 20.8 ± 0.5"
    )

def test_condensate_lb_h(ref):
    """Condensate flow: 39.3 lb/h ± 2.0
    Note: condensate uses omega_sat(T_ot) as the simplified outlet condition.
    """
    assert abs(ref['condensate_lb_h'] - 39.3) <= 2.0, (
        f"condensate = {ref['condensate_lb_h']} lb/h — expected 39.3 ± 2.0"
    )


# ── Physics invariants ───────────────────────────────────────────────────────

def test_tube_out_above_shell_in(ref):
    """Counterflow: tube outlet must be warmer than shell inlet."""
    assert ref['tube_out_F'] > REF_INPUTS['shell_temp_in_F'], (
        f"tube_out {ref['tube_out_F']}°F ≤ shell_in {REF_INPUTS['shell_temp_in_F']}°F — impossible counterflow"
    )

def test_shell_out_above_shell_in(ref):
    """Shell-side water must be warmed by the hot gas."""
    assert ref['shell_out_F'] > REF_INPUTS['shell_temp_in_F']

def test_heat_positive(ref):
    assert ref['Q_Btu_h'] > 0

def test_pressuredrops_positive(ref):
    assert ref['dP_tube_psi'] > 0
    assert ref['dP_shell_psi'] > 0

def test_condensate_positive(ref):
    """Reference case conditions cause condensation — must be > 0."""
    assert ref['condensate_lb_h'] > 0

def test_wall_temps_four_values(ref):
    assert len(ref['tube_wall_temps_F']) == 4

def test_all_required_keys(ref):
    required = [
        'Q_Btu_h', 'tube_out_F', 'shell_out_F', 'dP_tube_psi', 'dP_shell_psi',
        'LMTD_R', 'overall_U_btu', 'area_ft2', 'condensate_lb_h',
        'dew_point_F', 'tube_Re', 'shell_Re', 'tube_HTC_btu', 'shell_HTC_btu',
        'tube_wall_temps_F', 'condensing_Btu_h', 'condensing_pct',
    ]
    missing = [k for k in required if k not in ref]
    assert not missing, f"Missing output keys: {missing}"
