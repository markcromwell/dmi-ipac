"""
Live HTTP integration test — validates a deployed instance.
Run: python tests/test_live.py https://your-app.vercel.app
     python tests/test_live.py http://localhost:8888  (for local Vercel dev)

This test would have caught the Netlify Python function failure immediately.
"""
import sys, json, urllib.request, urllib.error

TOLERANCE = 0.05   # 5% on all outputs

REF_INPUTS = {
    'model': 'W0230', 'bundle_type': 'Fixed', 'tube_type': 'Std groove',
    'tube_material': 'Stainless (S3040*)', 'tube_fluid': 'Air',
    'tube_pressure_psig': 150, 'tube_temp_in_F': 250,
    'tube_flow': 1423, 'tube_flow_uom': 'Scfm', 'tube_fouling': 0,
    'shell_fluid': 'Water', 'shell_temp_in_F': 70,
    'shell_flow': 60, 'shell_flow_uom': 'USgpm', 'shell_fouling': 0,
    'surface_area_margin': 0,
    'suction_pressure_psia': 14.7, 'suction_temp_F': 85, 'suction_rh_pct': 36,
}

REF_EXPECTED = {
    'Q_Btu_h':         292245,
    'tube_out_F':      93.6,
    'shell_out_F':     79.8,
    'dP_tube_psi':     9.06,
    'dP_shell_psi':    7.55,
    'condensate_lb_h': 39.3,
    'LMTD_R':          74.2,
    'overall_U_btu':   190,
    'area_ft2':        20.8,
}


def call_api(base_url, inputs):
    # Try Vercel path first, then Netlify
    for path in ['/api/calculate', '/.netlify/functions/calculate']:
        url = base_url.rstrip('/') + path
        data = json.dumps(inputs).encode()
        req = urllib.request.Request(url, data=data,
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode()
                ct = r.headers.get('Content-Type', '')
                if 'json' not in ct:
                    print(f'  WARN: {path} returned Content-Type: {ct!r}')
                    print(f'  Body snippet: {body[:200]}')
                    continue
                return json.loads(body), path
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 404:
                continue   # try next path
            raise RuntimeError(f'{path} HTTP {e.code}: {body[:300]}')
    raise RuntimeError(f'No working API path found at {base_url}')


def run(base_url):
    print(f'\n=== DMI-IPAC Live Test: {base_url} ===\n')
    passed = failed = 0

    # ── 1. API reachability ──────────────────────────────────────────────────
    print('1. API reachability...')
    try:
        result, path = call_api(base_url, REF_INPUTS)
        print(f'   OK — responding at {path}')
        passed += 1
    except Exception as e:
        print(f'   FAIL — {e}')
        print('\n*** API not reachable. Stopping. ***')
        return False

    # ── 2. Response schema ───────────────────────────────────────────────────
    print('2. Response schema...')
    required_keys = list(REF_EXPECTED.keys()) + ['dew_point_F', 'tube_Re', 'shell_Re',
        'tube_HTC_btu', 'shell_HTC_btu', 'tube_wall_temps_F', 'condensing_Btu_h']
    missing = [k for k in required_keys if k not in result]
    if missing:
        print(f'   FAIL — missing keys: {missing}'); failed += 1
    else:
        print(f'   OK — all {len(required_keys)} keys present'); passed += 1

    # ── 3. Reference case accuracy ───────────────────────────────────────────
    print('3. Reference case accuracy (W0230, Air 250°F, Water 70°F)...')
    all_ok = True
    for key, exp in REF_EXPECTED.items():
        actual = result.get(key)
        if actual is None:
            print(f'   FAIL {key}: missing'); all_ok = False; continue
        err = abs(actual - exp) / exp
        status = 'OK' if err <= TOLERANCE else 'FAIL'
        if status == 'FAIL': all_ok = False
        print(f'   {status:4s} {key:<22} got={actual:<10} exp={exp:<10} err={err*100:.1f}%')
    if all_ok: passed += 1
    else: failed += 1

    # ── 4. Physics checks ────────────────────────────────────────────────────
    print('4. Physics checks...')
    checks = [
        ('tube_out > shell_in', result.get('tube_out_F', 0) > REF_INPUTS['shell_temp_in_F']),
        ('shell_out > shell_in', result.get('shell_out_F', 0) > REF_INPUTS['shell_temp_in_F']),
        ('Q > 0',               result.get('Q_Btu_h', 0) > 0),
        ('dP_tube > 0',         result.get('dP_tube_psi', 0) > 0),
        ('dP_shell > 0',        result.get('dP_shell_psi', 0) > 0),
        ('condensate > 0',      result.get('condensate_lb_h', 0) > 0),
        ('4 wall temps',        len(result.get('tube_wall_temps_F', [])) == 4),
    ]
    all_ok = True
    for name, ok in checks:
        print(f'   {"OK  " if ok else "FAIL"} {name}')
        if not ok: all_ok = False
    if all_ok: passed += 1
    else: failed += 1

    # ── 5. Static assets reachable ───────────────────────────────────────────
    print('5. Frontend (index.html)...')
    try:
        req = urllib.request.Request(base_url.rstrip('/') + '/')
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode('utf-8', errors='replace')
            if 'DIVERSIFIED MANUFACTURING' in body:
                print('   OK — DMI header found'); passed += 1
            else:
                print('   FAIL — index.html served but DMI header missing'); failed += 1
    except Exception as e:
        print(f'   FAIL — {e}'); failed += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    total = passed + failed
    print(f'\n{"="*45}')
    print(f'RESULT: {passed}/{total} checks passed')
    if failed == 0:
        print('ALL TESTS PASSED ✓')
    else:
        print(f'{failed} FAILED — app is NOT ready')
    print('='*45)
    return failed == 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tests/test_live.py <base-url>')
        print('  e.g. python tests/test_live.py https://dmi-ipac.vercel.app')
        sys.exit(1)
    ok = run(sys.argv[1])
    sys.exit(0 if ok else 1)
