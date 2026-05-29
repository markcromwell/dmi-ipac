"""
Integration tests for the DMI-IPAC API endpoint.
Requires the local dev server running: netlify dev

These tests are automatically skipped if the server isn't reachable,
so CI never breaks when netlify dev isn't running.

To run:
  netlify dev          # in one terminal
  pytest netlify/functions/tests/test_calculate_api.py -v   # in another
"""
import pytest

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

API_URL = 'http://localhost:8888/.netlify/functions/calculate'


def _server_running(url=API_URL):
    """Return True if the dev server is reachable."""
    if not HAS_REQUESTS:
        return False
    try:
        requests.get(url.replace('/.netlify/functions/calculate', '/'),
                     timeout=1)
        return True
    except Exception:
        return False


skip_if_no_server = pytest.mark.skipif(
    not _server_running(),
    reason='netlify dev not running — start with: netlify dev'
)

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


@skip_if_no_server
def test_api_returns_200():
    r = requests.post(API_URL, json=REF_INPUTS, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


@skip_if_no_server
def test_api_returns_json_not_html():
    """Regression: API must return JSON, not an HTML error page."""
    r = requests.post(API_URL, json=REF_INPUTS, timeout=30)
    ct = r.headers.get('Content-Type', '')
    assert 'json' in ct.lower(), (
        f"Content-Type is {ct!r} — got HTML instead of JSON. "
        f"Body: {r.text[:200]}"
    )


@skip_if_no_server
def test_api_cors_headers():
    """CORS headers must be present so the browser can call the function."""
    r = requests.post(API_URL, json=REF_INPUTS, timeout=30)
    assert 'access-control-allow-origin' in r.headers, \
        "Missing Access-Control-Allow-Origin header"


@skip_if_no_server
def test_api_options_preflight():
    """Browser preflight OPTIONS must return 200."""
    r = requests.options(API_URL,
                         headers={'Origin': 'http://localhost:8888',
                                  'Access-Control-Request-Method': 'POST'},
                         timeout=5)
    assert r.status_code == 200, f"OPTIONS returned {r.status_code}"


@skip_if_no_server
def test_api_reference_case_values():
    """End-to-end: POST reference inputs, check all key outputs."""
    r = requests.post(API_URL, json=REF_INPUTS, timeout=30)
    assert r.status_code == 200
    d = r.json()

    assert abs(d['Q_Btu_h']         - 292245) <= 100,  f"Q = {d['Q_Btu_h']}"
    assert abs(d['tube_out_F']       - 93.6)   <= 0.2,  f"tube_out = {d['tube_out_F']}"
    assert abs(d['shell_out_F']      - 79.8)   <= 0.2,  f"shell_out = {d['shell_out_F']}"
    assert abs(d['dP_tube_psi']      - 9.06)   <= 0.1,  f"dP_tube = {d['dP_tube_psi']}"
    assert abs(d['dP_shell_psi']     - 7.55)   <= 0.1,  f"dP_shell = {d['dP_shell_psi']}"
    assert abs(d['condensate_lb_h']  - 39.3)   <= 0.5,  f"condensate = {d['condensate_lb_h']}"


@skip_if_no_server
def test_api_unknown_model_returns_500():
    """Unknown model code must return 500 with an error message, not crash silently."""
    bad = dict(REF_INPUTS, model='W9999')
    r = requests.post(API_URL, json=bad, timeout=10)
    assert r.status_code == 500
    assert 'error' in r.json()


@skip_if_no_server
def test_api_empty_body_returns_error():
    """Empty body must return 500 with a JSON error, not an HTML traceback."""
    r = requests.post(API_URL, data='', headers={'Content-Type': 'application/json'}, timeout=10)
    ct = r.headers.get('Content-Type', '')
    assert 'json' in ct.lower(), f"Empty-body error returned HTML: {r.text[:100]}"
