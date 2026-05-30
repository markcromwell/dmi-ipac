"""
wcac_cli — command-line interface for the WCAC heat exchanger calculator.

Usage:
    python -m targets.cli.wcac_cli --model W0230 --tube-temp 250 --shell-temp 70
    python -m targets.cli.wcac_cli --json inputs.json
    python -m targets.cli.wcac_cli --reference            # run the reference case
    python -m targets.cli.wcac_cli --list-models
    python -m targets.cli.wcac_cli --datasheet out.txt    # write a datasheet

Every front-end imports the SAME wcac library; this CLI adds only argument
parsing and output formatting.
"""
import sys
import os
import json
import argparse
from dataclasses import asdict, fields

# Make wcac importable when run from anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from wcac import (calculate, validate, WCACInputs, WCACResult,
                  list_models, Severity)


def build_parser():
    p = argparse.ArgumentParser(
        prog='wcac',
        description='DMI IPAC / WCAC Heat Exchanger performance calculator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    p.add_argument('--reference', action='store_true',
                   help='run the W0230 reference case and exit')
    p.add_argument('--list-models', action='store_true',
                   help='list all valid model codes and exit')
    p.add_argument('--json', metavar='FILE',
                   help='read inputs from a JSON file (keys = WCACInputs fields)')
    p.add_argument('--datasheet', metavar='FILE',
                   help='write a formatted text datasheet to FILE')
    p.add_argument('--output-json', metavar='FILE',
                   help='write results as JSON to FILE')
    p.add_argument('--no-validate', action='store_true',
                   help='skip input validation (compute anything)')

    g = p.add_argument_group('aftercooler')
    g.add_argument('--model', default='W0230')
    g.add_argument('--bundle', default='Fixed', choices=['Fixed', 'Removable'])
    g.add_argument('--tube-type', default='Std groove', choices=['Std groove', 'Plain'])
    g.add_argument('--material', default='Stainless (S3040*)')

    g = p.add_argument_group('tube side (gas)')
    g.add_argument('--tube-fluid', default='Air')
    g.add_argument('--tube-press', type=float, default=150, metavar='PSIG')
    g.add_argument('--tube-temp', type=float, default=250, metavar='F')
    g.add_argument('--tube-flow', type=float, default=1423)
    g.add_argument('--tube-flow-uom', default='Scfm')
    g.add_argument('--tube-fouling', type=float, default=0.0)

    g = p.add_argument_group('shell side (liquid)')
    g.add_argument('--shell-fluid', default='Water')
    g.add_argument('--shell-temp', type=float, default=70, metavar='F')
    g.add_argument('--shell-flow', type=float, default=60)
    g.add_argument('--shell-flow-uom', default='USgpm')
    g.add_argument('--shell-fouling', type=float, default=0.0)
    g.add_argument('--glycol', type=float, default=40, metavar='PCT')

    g = p.add_argument_group('compressor suction')
    g.add_argument('--suction-press', type=float, default=14.7, metavar='PSIA')
    g.add_argument('--suction-temp', type=float, default=85, metavar='F')
    g.add_argument('--suction-rh', type=float, default=36, metavar='PCT')

    g = p.add_argument_group('performance')
    g.add_argument('--margin', type=float, default=0.0, metavar='PCT',
                   help='surface area margin %%')

    return p


def args_to_inputs(a) -> WCACInputs:
    return WCACInputs(
        model=a.model, bundle_type=a.bundle, tube_type=a.tube_type,
        tube_material=a.material,
        tube_fluid=a.tube_fluid, tube_pressure_psig=a.tube_press,
        tube_temp_in_F=a.tube_temp, tube_flow=a.tube_flow,
        tube_flow_uom=a.tube_flow_uom, tube_fouling=a.tube_fouling,
        shell_fluid=a.shell_fluid, shell_temp_in_F=a.shell_temp,
        shell_flow=a.shell_flow, shell_flow_uom=a.shell_flow_uom,
        shell_fouling=a.shell_fouling, glycol_concentration=a.glycol,
        suction_pressure_psia=a.suction_press, suction_temp_F=a.suction_temp,
        suction_rh_pct=a.suction_rh, surface_area_margin=a.margin,
    )


def format_datasheet(inp: WCACInputs, res: WCACResult) -> str:
    L = []
    L.append('=' * 64)
    L.append('  DIVERSIFIED MANUFACTURING INC.')
    L.append('  IPAC Air Cooled Heat Exchanger - Performance Datasheet')
    L.append('  410 Ohio Street, Lockport NY 14094  |  sales@dmimfg.com')
    L.append('=' * 64)
    L.append('')
    L.append(f'  Model: {inp.model}    Bundle: {inp.bundle_type}    '
             f'Tube: {inp.tube_type}    Material: {inp.tube_material}')
    L.append('')
    L.append('  INPUTS')
    L.append('  ' + '-' * 60)
    L.append(f'  Tube side : {inp.tube_fluid}, {inp.tube_pressure_psig:g} psig, '
             f'{inp.tube_temp_in_F:g} F, {inp.tube_flow:g} {inp.tube_flow_uom}')
    L.append(f'  Shell side: {inp.shell_fluid}, {inp.shell_flow:g} '
             f'{inp.shell_flow_uom}, {inp.shell_temp_in_F:g} F')
    L.append(f'  Suction   : {inp.suction_pressure_psia:g} psia, '
             f'{inp.suction_temp_F:g} F, {inp.suction_rh_pct:g}% RH')
    if inp.tube_fouling or inp.shell_fouling:
        L.append(f'  Fouling   : tube {inp.tube_fouling:g}, shell {inp.shell_fouling:g} R.ft2.h/Btu')
    if inp.surface_area_margin:
        L.append(f'  SA margin : {inp.surface_area_margin:g}%')
    L.append('')
    L.append('  RESULTS')
    L.append('  ' + '-' * 60)
    rows = [
        ('Total heat transfer',  f'{res.Q_Btu_h:,.0f}',  'Btu/h'),
        ('Tube outlet temp',     f'{res.tube_out_F:.1f}', 'F'),
        ('Shell outlet temp',    f'{res.shell_out_F:.1f}', 'F'),
        ('Dew point at inlet',   f'{res.dew_point_F:.1f}', 'F'),
        ('Tube pressure loss',   f'{res.dP_tube_psi:.2f}', 'psi'),
        ('Shell pressure loss',  f'{res.dP_shell_psi:.2f}', 'psi'),
        ('Tube Reynolds',        f'{res.tube_Re:,.0f}', '-'),
        ('Shell Reynolds',       f'{res.shell_Re:,.0f}', '-'),
        ('Tube effective HTC',   f'{res.tube_HTC_btu:.0f}', 'Btu/h.ft2.R'),
        ('Shell effective HTC',  f'{res.shell_HTC_btu:.0f}', 'Btu/h.ft2.R'),
        ('Overall HTC (U)',      f'{res.overall_U_btu:.0f}', 'Btu/h.ft2.R'),
        ('LMTD',                 f'{res.LMTD_R:.1f}', 'R'),
        ('Surface area',         f'{res.area_ft2:.1f}', 'ft2'),
        ('Number of tubes',      f'{res.Nt}', '-'),
        ('Condensate flow',      f'{res.condensate_lb_h:.1f}', 'lb/h'),
        ('Condensing heat',      f'{res.condensing_Btu_h:,.0f}',
                                 f'Btu/h ({res.condensing_pct:.1f}%)'),
    ]
    for label, val, unit in rows:
        L.append(f'  {label:.<26s} {val:>14s}  {unit}')
    L.append('')
    L.append(f'  Tube surface temps: {", ".join(f"{t:.0f}" for t in res.tube_wall_temps_F)} F')
    L.append('=' * 64)
    return '\n'.join(L)


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)

    if a.list_models:
        print('Valid models:', ', '.join(list_models()))
        return 0

    if a.json:
        with open(a.json) as f:
            data = json.load(f)
        valid = {fld.name for fld in fields(WCACInputs)}
        inp = WCACInputs(**{k: v for k, v in data.items() if k in valid})
    else:
        inp = args_to_inputs(a)

    # Validation
    issues = validate(inp)
    errors = [i for i in issues if i.severity is Severity.ERROR]
    warnings = [i for i in issues if i.severity is Severity.WARNING]
    for w in warnings:
        print(f'  WARNING [{w.field}]: {w.message}', file=sys.stderr)
    if errors and not a.no_validate:
        for e in errors:
            print(f'  ERROR [{e.field}]: {e.message}', file=sys.stderr)
        print('\nRefusing to compute with invalid inputs. Use --no-validate to override.',
              file=sys.stderr)
        return 2

    res = calculate(inp)

    sheet = format_datasheet(inp, res)
    print(sheet)

    if a.datasheet:
        with open(a.datasheet, 'w', encoding='utf-8') as f:
            f.write(sheet)
        print(f'\nDatasheet written to {a.datasheet}')

    if a.output_json:
        with open(a.output_json, 'w', encoding='utf-8') as f:
            json.dump(asdict(res), f, indent=2)
        print(f'Results JSON written to {a.output_json}')

    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
