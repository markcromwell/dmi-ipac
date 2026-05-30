"""
xl_driver — drive the ORIGINAL W1279 spreadsheet via Excel COM (xlwings).

The spreadsheet itself is NEVER modified or saved. We open a temporary COPY,
set inputs, let Excel recalculate, read outputs, then discard the copy.
The pristine original at SOURCE_XLSM stays byte-for-byte untouched.

This is the ground-truth oracle for validating the wcac Python library.

Requires: Windows or Mac with Excel installed, and `pip install xlwings`.
"""
import os
import shutil
import tempfile
from dataclasses import dataclass, asdict
from typing import Optional

SOURCE_XLSM = r"C:\Users\markc\Downloads\W1279 DMI WCAC Design program I0-1.xlsm"


# ── Cell map (design sheet) ───────────────────────────────────────────────────
# Verified against the spreadsheet on 2026-05-30.

# IMPORTANT: the tube-side gas mass flow is NOT entered directly.
# It is derived from the compressor suction flow (D9) at suction conditions
# (D5/D6/D7).  D20 is a DISPLAY formula showing that same mass flow in the
# unit selected at E20 (default Scfm).  Therefore D9 is the real flow input
# and D20 is read as an OUTPUT.  The shell flow (I20) IS a direct input.
INPUT_CELLS = {
    # Compressor (these set the tube-side gas mass flow)
    'suction_pressure_value': 'D5',   'suction_pressure_uom': 'E5',
    'suction_temp_value':     'D6',   'suction_temp_uom':     'E6',
    'suction_rh_value':       'D7',
    'suction_flow_value':     'D9',   'suction_flow_uom':     'E9',
    'comp_stages':            'D10',
    # Aftercooler config
    'model':                  'I5',
    'bundle_type':            'I7',
    'tube_design_pressure':   'I8',
    'tube_type':              'I9',
    'tube_material':          'I10',
    'tube_length_type':       'I11',
    # Tube side (flow is derived from suction — only fluid/P/T/fouling are inputs)
    'tube_fluid':             'D18',
    'tube_pressure_value':    'D19',  'tube_pressure_uom':    'E19',
    'tube_flow_display_uom':  'E20',  # sets the display unit for D20 output
    'tube_temp_value':        'D21',  'tube_temp_uom':        'E21',
    'tube_fouling':           'D27',
    # Shell side (flow IS a direct input)
    'shell_fluid':            'I18',
    'shell_glycol_conc':      'I19',
    'shell_flow_value':       'I20',  'shell_flow_uom':       'J20',
    'shell_temp_value':       'I21',  'shell_temp_uom':       'J21',
    'shell_fouling':          'I27',
    # Performance
    'surface_area_margin':    'F29',
}

OUTPUT_CELLS = {
    'tube_flow_scfm':   'D20',   # derived tube-side flow in display unit (Scfm)
    'tube_out_F':       'D22',
    'dew_point_F':      'D23',
    'dP_tube_psi':      'D24',
    'tube_Re':          'D25',
    'tube_HTC_btu':     'D26',
    'shell_out_F':      'I22',
    'tube_wall_temps':  'I23',   # string e.g. "123, 117, 124, 78.6°F"
    'dP_shell_psi':     'I24',
    'shell_Re':         'I25',
    'shell_HTC_btu':    'I26',
    'area_ft2':         'F30',
    'overall_U_btu':    'F31',
    'Q_Btu_h':          'F32',
    'condensing_Btu_h': 'F33',
    'condensate_lb_h':  'F34',
}


@dataclass
class XLScenario:
    """One test scenario expressed in the spreadsheet's own input terms.

    Note: the tube-side gas flow is specified at the COMPRESSOR SUCTION
    (suction_flow + suction_flow_uom).  The spreadsheet derives the tube-side
    mass flow from this; D20 (Scfm) is read back as a derived output.
    """
    # Compressor (sets tube-side gas mass flow)
    suction_pressure_psia: float = 14.7
    suction_temp_F:        float = 85.0
    suction_rh_pct:        float = 36.0
    suction_flow:          float = 1500.0
    suction_flow_uom:      str   = 'Acfm'
    comp_stages:           str   = 'No'
    # Config
    model:                 str   = 'W0230'
    bundle_type:           str   = 'Fixed'
    tube_design_pressure:  float = 300.0
    tube_type:             str   = 'Std groove'
    tube_material:         str   = 'Stainless (S3040*)'
    tube_length_type:      str   = 'Standard'
    # Tube side
    tube_fluid:            str   = 'Air'
    tube_pressure_psig:    float = 150.0
    tube_temp_in_F:        float = 250.0
    tube_fouling:          float = 0.0
    # Shell side
    shell_fluid:           str   = 'Water'
    shell_glycol_conc:     float = 50.0
    shell_flow:            float = 60.0
    shell_flow_uom:        str   = 'USgpm'
    shell_temp_in_F:       float = 70.0
    shell_fouling:         float = 0.0
    # Performance
    surface_area_margin:   float = 0.0


class SpreadsheetOracle:
    """Opens a disposable copy of the spreadsheet and runs scenarios through Excel.

    Usage::

        with SpreadsheetOracle() as oracle:
            result = oracle.run(XLScenario(tube_temp_in_F=300))
            print(result['Q_Btu_h'])

    Keeps one Excel instance and one workbook copy alive for the whole session
    (opening Excel is slow ~3-5 s; reuse it across all scenarios).
    """

    def __init__(self, source: str = SOURCE_XLSM, visible: bool = False):
        self.source = source
        self.visible = visible
        self._app = None
        self._wb = None
        self._tmpdir = None
        self._tmppath = None

    def __enter__(self):
        import xlwings as xw
        if not os.path.exists(self.source):
            raise FileNotFoundError(f'Spreadsheet not found: {self.source}')

        # Make a disposable copy so the original is never touched
        self._tmpdir = tempfile.mkdtemp(prefix='wcac_oracle_')
        self._tmppath = os.path.join(self._tmpdir, 'oracle_copy.xlsm')
        shutil.copy2(self.source, self._tmppath)

        self._app = xw.App(visible=self.visible)
        self._app.display_alerts = False
        self._app.screen_updating = False
        # Force automatic calculation
        self._app.api.Calculation = -4105  # xlCalculationAutomatic
        self._wb = self._app.books.open(self._tmppath)
        return self

    def __exit__(self, *exc):
        try:
            if self._wb is not None:
                self._wb.close()
        finally:
            if self._app is not None:
                self._app.quit()
            if self._tmpdir and os.path.isdir(self._tmpdir):
                shutil.rmtree(self._tmpdir, ignore_errors=True)

    def run(self, sc: XLScenario) -> dict:
        """Set inputs, recalculate, return outputs as a dict."""
        d = self._wb.sheets['design']

        def put(cell, value):
            d.range(cell).value = value

        # ── Compressor (sets tube-side gas mass flow) ───────────────────
        put(INPUT_CELLS['suction_pressure_uom'],   'psi(a)')
        put(INPUT_CELLS['suction_pressure_value'], sc.suction_pressure_psia)
        put(INPUT_CELLS['suction_temp_uom'],       '°F')
        put(INPUT_CELLS['suction_temp_value'],     sc.suction_temp_F)
        put(INPUT_CELLS['suction_rh_value'],       sc.suction_rh_pct)
        put(INPUT_CELLS['suction_flow_uom'],       sc.suction_flow_uom)
        put(INPUT_CELLS['suction_flow_value'],     sc.suction_flow)
        put(INPUT_CELLS['comp_stages'],            sc.comp_stages)

        # ── Config ───────────────────────────────────────────────────────
        put(INPUT_CELLS['model'],                  sc.model)
        put(INPUT_CELLS['bundle_type'],            sc.bundle_type)
        put(INPUT_CELLS['tube_design_pressure'],   sc.tube_design_pressure)
        put(INPUT_CELLS['tube_type'],              sc.tube_type)
        put(INPUT_CELLS['tube_material'],          sc.tube_material)
        put(INPUT_CELLS['tube_length_type'],       sc.tube_length_type)

        # ── Tube side (flow derived from suction; only set display unit) ─
        put(INPUT_CELLS['tube_fluid'],             sc.tube_fluid)
        put(INPUT_CELLS['tube_pressure_uom'],      'psig')
        put(INPUT_CELLS['tube_pressure_value'],    sc.tube_pressure_psig)
        put(INPUT_CELLS['tube_flow_display_uom'],  'Scfm')
        put(INPUT_CELLS['tube_temp_uom'],          '°F')
        put(INPUT_CELLS['tube_temp_value'],        sc.tube_temp_in_F)
        put(INPUT_CELLS['tube_fouling'],           sc.tube_fouling)

        # ── Shell side ───────────────────────────────────────────────────
        put(INPUT_CELLS['shell_fluid'],            sc.shell_fluid)
        if sc.shell_fluid in ('Water/ethylene glycol', 'Water/propylene glycol'):
            put(INPUT_CELLS['shell_glycol_conc'],  sc.shell_glycol_conc)
        put(INPUT_CELLS['shell_flow_uom'],         sc.shell_flow_uom)
        put(INPUT_CELLS['shell_flow_value'],       sc.shell_flow)
        put(INPUT_CELLS['shell_temp_uom'],         '°F')
        put(INPUT_CELLS['shell_temp_value'],       sc.shell_temp_in_F)
        put(INPUT_CELLS['shell_fouling'],          sc.shell_fouling)

        # ── Performance ──────────────────────────────────────────────────
        put(INPUT_CELLS['surface_area_margin'],    sc.surface_area_margin)

        # Force a full recalculation
        self._app.api.CalculateFull()

        # ── Read outputs ─────────────────────────────────────────────────
        out = {}
        for key, cell in OUTPUT_CELLS.items():
            out[key] = d.range(cell).value
        return out


def smoke_test():
    """Quick check that the oracle runs the reference case."""
    with SpreadsheetOracle() as oracle:
        r = oracle.run(XLScenario())
        print('Spreadsheet reference case (W0230, Air 250F / Water 70F):')
        print(f"  Q           = {r['Q_Btu_h']:>12,.0f} Btu/h")
        print(f"  Tube outlet = {r['tube_out_F']:>12.1f} °F")
        print(f"  Shell outlet= {r['shell_out_F']:>12.1f} °F")
        print(f"  dP tube     = {r['dP_tube_psi']:>12.2f} psi")
        print(f"  dP shell    = {r['dP_shell_psi']:>12.2f} psi")
        print(f"  Condensate  = {r['condensate_lb_h']:>12.1f} lb/h")
    return r


if __name__ == '__main__':
    smoke_test()
