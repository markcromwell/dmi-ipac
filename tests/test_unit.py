"""
Unit tests for the DMI-IPAC calculation engine.
Run: python -m pytest tests/ -v
These tests run locally against the Python module — no network required.
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
from calculate import solve, handler

# ── Reference case inputs ────────────────────────────────────────────────────
REF = {
    'model': 'W0230', 'bundle_type': 'Fixed', 'tube_type': 'Std groove',
    'tube_material': 'Stainless (S3040*)', 'tube_fluid': 'Air',
    'tube_pressure_psig': 150, 'tube_temp_in_F': 250,
    'tube_flow': 1423, 'tube_flow_uom': 'Scfm', 'tube_fouling': 0,
    'shell_fluid': 'Water', 'shell_temp_in_F': 70,
    'shell_flow': 60, 'shell_flow_uom': 'USgpm', 'shell_fouling': 0,
    'surface_area_margin': 0,
    'suction_pressure_psia': 14.7, 'suction_temp_F': 85, 'suction_rh_pct': 36,
}

# Expected values from spreadsheet W1279 I0-1 (all within 5% tolerance)
REF_EXPECTED = {
    'Q_Btu_h':         (292245, 0.05),
    'tube_out_F':      (93.6,   0.05),
    'shell_out_F':     (79.8,   0.03),
    'dP_tube_psi':     (9.06,   0.05),
    'dP_shell_psi':    (7.55,   0.05),
    'condensate_lb_h': (39.3,   0.10),
    'LMTD_R':          (74.2,   0.05),
    'overall_U_btu':   (190,    0.08),
    'area_ft2':        (20.8,   0.02),
}


class TestReferenceCase:
    def setup_method(self):
        self.r = solve(REF)

    def test_all_keys_present(self):
        required = ['Q_Btu_h', 'tube_out_F', 'shell_out_F', 'dP_tube_psi',
                    'dP_shell_psi', 'condensate_lb_h', 'LMTD_R', 'overall_U_btu',
                    'area_ft2', 'dew_point_F', 'tube_Re', 'shell_Re',
                    'tube_HTC_btu', 'shell_HTC_btu', 'tube_wall_temps_F',
                    'condensing_Btu_h', 'condensing_pct']
        for k in required:
            assert k in self.r, f'Missing key: {k}'

    @pytest.mark.parametrize('key,expected,tol', [
        (k, v[0], v[1]) for k, v in REF_EXPECTED.items()
    ])
    def test_reference_values(self, key, expected, tol):
        actual = self.r[key]
        err = abs(actual - expected) / expected
        assert err <= tol, (
            f'{key}: got {actual}, expected {expected}, '
            f'error {err*100:.1f}% > tolerance {tol*100:.0f}%'
        )

    def test_physics_tube_out_above_shell_in(self):
        """Tube outlet must be warmer than shell inlet (counterflow, no chiller)."""
        assert self.r['tube_out_F'] > REF['shell_temp_in_F'], (
            f"tube_out={self.r['tube_out_F']} <= shell_in={REF['shell_temp_in_F']}"
        )

    def test_physics_shell_out_above_shell_in(self):
        """Shell outlet must be warmer than shell inlet."""
        assert self.r['shell_out_F'] > REF['shell_temp_in_F']

    def test_physics_positive_heat(self):
        assert self.r['Q_Btu_h'] > 0

    def test_physics_positive_pressuredrops(self):
        assert self.r['dP_tube_psi'] > 0
        assert self.r['dP_shell_psi'] > 0

    def test_condensate_positive(self):
        """Reference case has condensation — condensate must be > 0."""
        assert self.r['condensate_lb_h'] > 0

    def test_wall_temps_length(self):
        assert len(self.r['tube_wall_temps_F']) == 4

    def test_bell_delaware_factors(self):
        """Jc, Jl, Jb, Jr, Js should all be between 0 and 2."""
        for k in ('Jc', 'Jl', 'Jb', 'Jr', 'Js'):
            if k in self.r:
                assert 0 < self.r[k] <= 2.0, f'{k}={self.r[k]} out of range'


class TestModels:
    """Smoke test several models to ensure no crashes and physical results."""

    @pytest.mark.parametrize('model', ['W0035', 'W0110', 'W0490', 'W1400', 'W5000'])
    def test_model_runs(self, model):
        inputs = {**REF, 'model': model, 'tube_flow': 100, 'shell_flow': 30}
        r = solve(inputs)
        assert r['Q_Btu_h'] > 0
        assert r['tube_out_F'] > inputs['shell_temp_in_F']

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match='Unknown model'):
            solve({**REF, 'model': 'W9999'})


class TestFluids:
    @pytest.mark.parametrize('fluid', ['Air', 'Nitrogen', 'Carbon dioxide'])
    def test_gas_fluids(self, fluid):
        r = solve({**REF, 'tube_fluid': fluid})
        assert r['Q_Btu_h'] > 0
        assert r['tube_out_F'] > REF['shell_temp_in_F']

    @pytest.mark.parametrize('uom,flow', [
        ('Scfm', 1423), ('Acfm', 1500), ('lb/min', 50), ('kg/s', 0.82),
    ])
    def test_tube_flow_units(self, uom, flow):
        r = solve({**REF, 'tube_flow_uom': uom, 'tube_flow': flow})
        assert r['Q_Btu_h'] > 0

    @pytest.mark.parametrize('uom,flow', [
        ('USgpm', 60), ('lb/min', 500), ('kg/s', 3.8),
    ])
    def test_shell_flow_units(self, uom, flow):
        r = solve({**REF, 'shell_flow_uom': uom, 'shell_flow': flow})
        assert r['Q_Btu_h'] > 0


class TestHandler:
    """Test the Vercel HTTP handler with mock requests."""

    def test_handler_post_returns_json(self):
        import json
        from io import BytesIO
        from unittest.mock import MagicMock

        body = json.dumps(REF).encode()
        req = MagicMock()
        req.headers = {'Content-Length': str(len(body)), 'Content-Type': 'application/json'}
        req.rfile = BytesIO(body)

        responses = []
        h = handler.__new__(handler)
        h.headers = req.headers
        h.rfile = req.rfile
        h.wfile = BytesIO()
        h.send_response = lambda code: responses.append(code)
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None

        h.do_POST()
        assert responses[0] == 200
        h.wfile.seek(0)
        result = json.loads(h.wfile.read())
        assert 'Q_Btu_h' in result
        assert result['Q_Btu_h'] > 200000

    def test_handler_options_returns_200(self):
        from io import BytesIO
        from unittest.mock import MagicMock

        responses = []
        h = handler.__new__(handler)
        h.headers = {}
        h.rfile = BytesIO(b'')
        h.wfile = BytesIO()
        h.send_response = lambda code: responses.append(code)
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None

        h.do_OPTIONS()
        assert responses[0] == 200
