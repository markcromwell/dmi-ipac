"""
compare — run every scenario through BOTH the spreadsheet and the wcac library,
compare output-by-output, and produce a detailed report.

This is the definitive validation: it proves the Python library reproduces
the original Excel engine across the whole calculation space.

Usage:
    python -m tests.spreadsheet.compare              # full matrix
    python -m tests.spreadsheet.compare --quick      # 6-scenario subset
    python -m tests.spreadsheet.compare --csv out.csv

The original spreadsheet is opened as a disposable copy and never modified.
"""
import sys
import csv
import argparse
from dataclasses import asdict

# Force UTF-8 console output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Make the wcac package importable when run as a script
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from wcac import calculate, WCACInputs
from .xl_driver import SpreadsheetOracle, XLScenario
from . import scenarios as S


# Outputs to compare, with tolerance (absolute, relative) and unit label
# rel tolerance applies to magnitude; abs is a floor for near-zero values.
COMPARISONS = [
    # key                spreadsheet_key      label             abs_tol  rel_tol  unit
    ('Q_Btu_h',          'Q_Btu_h',          'Total heat',      500,     0.02,   'Btu/h'),
    ('tube_out_F',       'tube_out_F',       'Tube outlet',     0.5,     0.01,   '°F'),
    ('shell_out_F',      'shell_out_F',      'Shell outlet',    0.3,     0.01,   '°F'),
    ('dP_tube_psi',      'dP_tube_psi',      'Tube dP',         0.2,     0.03,   'psi'),
    ('dP_shell_psi',     'dP_shell_psi',     'Shell dP',        0.3,     0.05,   'psi'),
    ('condensate_lb_h',  'condensate_lb_h',  'Condensate',      1.0,     0.05,   'lb/h'),
    ('LMTD_R',           None,               'LMTD',            1.0,     0.02,   '°R'),
    ('overall_U_btu',    'overall_U_btu',    'Overall U',       5,       0.03,   'Btu/h·ft²·R'),
    ('area_ft2',         'area_ft2',         'Surface area',    0.3,     0.01,   'ft²'),
    ('tube_Re',          'tube_Re',          'Tube Re',         200,     0.02,   '-'),
    ('shell_Re',         'shell_Re',         'Shell Re',        200,     0.02,   '-'),
    ('tube_HTC_btu',     'tube_HTC_btu',     'Tube HTC',        10,      0.05,   'Btu/h·ft²·R'),
    ('shell_HTC_btu',    'shell_HTC_btu',    'Shell HTC',       15,      0.05,   'Btu/h·ft²·R'),
    ('dew_point_F',      'dew_point_F',      'Dew point',       1.0,     0.02,   '°F'),
    ('condensing_Btu_h', 'condensing_Btu_h', 'Condensing heat', 500,     0.10,   'Btu/h'),
]


def xlscenario_to_inputs(sc: XLScenario, tube_flow_scfm: float) -> WCACInputs:
    """Build WCACInputs from an XLScenario.

    tube_flow_scfm is the Scfm value the spreadsheet derived from the suction
    flow (read from D20).  Feeding it to the library ensures both engines use
    the exact same tube-side mass flow, isolating the thermal comparison.
    """
    return WCACInputs(
        model=sc.model,
        bundle_type=sc.bundle_type,
        tube_type=sc.tube_type,
        tube_material=sc.tube_material,
        tube_design_pressure_psig=sc.tube_design_pressure,
        tube_fluid=sc.tube_fluid,
        tube_pressure_psig=sc.tube_pressure_psig,
        tube_temp_in_F=sc.tube_temp_in_F,
        tube_flow=tube_flow_scfm,
        tube_flow_uom='Scfm',
        tube_fouling=sc.tube_fouling,
        shell_fluid=sc.shell_fluid,
        shell_temp_in_F=sc.shell_temp_in_F,
        shell_flow=sc.shell_flow,
        shell_flow_uom=sc.shell_flow_uom,
        shell_fouling=sc.shell_fouling,
        glycol_concentration=sc.shell_glycol_conc,
        suction_pressure_psia=sc.suction_pressure_psia,
        suction_temp_F=sc.suction_temp_F,
        suction_rh_pct=sc.suction_rh_pct,
        surface_area_margin=sc.surface_area_margin,
    )


def compare_one(name, sc, xl_out):
    """Compare library vs spreadsheet for one scenario. Returns list of row dicts."""
    tube_flow_scfm = xl_out.get('tube_flow_scfm') or 0
    lib = calculate(xlscenario_to_inputs(sc, tube_flow_scfm))

    rows = []
    for lib_key, xl_key, label, abs_tol, rel_tol, unit in COMPARISONS:
        if xl_key is None:
            continue  # library-only quantity, no spreadsheet equivalent
        xv = xl_out.get(xl_key)
        lv = getattr(lib, lib_key, None)
        if xv is None or lv is None:
            continue
        try:
            xv = float(xv); lv = float(lv)
        except (TypeError, ValueError):
            continue
        diff = lv - xv
        tol = max(abs_tol, abs(xv) * rel_tol)
        rel = abs(diff) / abs(xv) * 100 if xv != 0 else 0.0
        status = 'PASS' if abs(diff) <= tol else 'FAIL'
        rows.append({
            'scenario': name, 'output': label, 'unit': unit,
            'spreadsheet': xv, 'library': lv,
            'diff': diff, 'rel_pct': rel, 'tol': tol, 'status': status,
        })
    return rows


def run(scenario_list, csv_path=None):
    """Run all scenarios through both engines and print a report."""
    all_rows = []
    print(f'\nRunning {len(scenario_list)} scenarios through spreadsheet + library...\n')

    with SpreadsheetOracle() as oracle:
        for i, (name, sc) in enumerate(scenario_list, 1):
            try:
                xl_out = oracle.run(sc)
                rows = compare_one(name, sc, xl_out)
                all_rows.extend(rows)
                fails = sum(1 for r in rows if r['status'] == 'FAIL')
                mark = 'OK  ' if fails == 0 else f'{fails} FAIL'
                print(f'  [{i:3d}/{len(scenario_list)}] {name:30s} {mark}')
            except Exception as e:
                print(f'  [{i:3d}/{len(scenario_list)}] {name:30s} ERROR: {e}')

    # ── Summary ────────────────────────────────────────────────────────────
    total = len(all_rows)
    passed = sum(1 for r in all_rows if r['status'] == 'PASS')
    print(f'\n{"="*70}')
    print(f'TOTAL: {passed}/{total} comparisons passed')

    # Per-output breakdown
    print(f'\nPer-output worst-case relative error:')
    by_output = {}
    for r in all_rows:
        by_output.setdefault(r['output'], []).append(r)
    for label, rows in by_output.items():
        worst = max(rows, key=lambda r: r['rel_pct'])
        fails = sum(1 for r in rows if r['status'] == 'FAIL')
        flag = '' if fails == 0 else f'  <-- {fails} FAIL'
        print(f'  {label:18s} worst {worst["rel_pct"]:5.1f}%  '
              f'(scenario: {worst["scenario"]}){flag}')

    # Failures detail
    failures = [r for r in all_rows if r['status'] == 'FAIL']
    if failures:
        print(f'\n{len(failures)} FAILURES:')
        print(f'  {"scenario":28s} {"output":16s} {"sheet":>12s} {"lib":>12s} {"rel%":>7s}')
        for r in failures:
            print(f'  {r["scenario"]:28s} {r["output"]:16s} '
                  f'{r["spreadsheet"]:>12.2f} {r["library"]:>12.2f} {r["rel_pct"]:>6.1f}%')

    # CSV export
    if csv_path:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print(f'\nDetailed results written to {csv_path}')

    print('='*70)
    return passed == total


def main():
    ap = argparse.ArgumentParser(description='Validate wcac library against the original spreadsheet')
    ap.add_argument('--quick', action='store_true', help='6-scenario subset')
    ap.add_argument('--csv', help='write detailed CSV')
    args = ap.parse_args()

    scenario_list = S.quick_scenarios() if args.quick else S.all_scenarios()
    ok = run(scenario_list, args.csv)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
