"""
extract_intermediates — read the VBA solver's intermediate output values from
the calc sheet, so the Python translation can be verified element-by-element
(not just on final design-sheet outputs).

The VBA Qsolver returns an array displayed across calc!B10:V10 (fouled row).
Matching every one of these intermediates proves the translation is faithful.

calc sheet intermediate cells (row 10 = fouled = the reported case):
  B10 Q (kW)        D10 U (W/m2K)     F10 dPt (kPa)
  H10 t2t (C)       I10 t2tw (C)      J10 totw (C)
  L10 tmtw (C)      M10 tmsw (C)      N10 A_dry (m2)
  O10 ht (W/m2K)    P10 hs (W/m2K)    Q10 htmt          R10 LMED (J/kg)
  S10 tsw_inlet     T10 tsw_2dry      U10 tsw_2wet      V10 tsw_outlet
Single-value cells:
  D28 Gs   D29 Res   J30 Gt   J31 Ret   D34 fs   J38 ft
  D23 tos  J26 tot   J23 omegait  I16 omegao  J28 tdpi(dewpoint C)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .xl_driver import SpreadsheetOracle, XLScenario, INPUT_CELLS

# Intermediate cells: name -> (sheet, cell)
INTERMEDIATE_CELLS = {
    'Q_kW':      ('calc', 'B10'),
    'U_Wm2K':    ('calc', 'D10'),
    'dpt_kPa':   ('calc', 'F10'),
    't2t_C':     ('calc', 'H10'),
    't2tw_C':    ('calc', 'I10'),
    'totw_C':    ('calc', 'J10'),
    'tmtw_C':    ('calc', 'L10'),
    'tmsw_C':    ('calc', 'M10'),
    'Areqdry':   ('calc', 'N10'),
    'ht_Wm2K':   ('calc', 'O10'),
    'hs_Wm2K':   ('calc', 'P10'),
    'htmt':      ('calc', 'Q10'),
    'LMED':      ('calc', 'R10'),
    # Single-value supporting cells
    'Gs':        ('calc', 'D28'),
    'Res':       ('calc', 'D29'),
    'Gt':        ('calc', 'J30'),
    'Ret':       ('calc', 'J31'),
    'fs':        ('calc', 'D34'),
    'ft':        ('calc', 'J38'),
    'tos_C':     ('calc', 'D23'),
    'tot_C':     ('calc', 'J26'),
    'omegait':   ('calc', 'J23'),
    'omegao':    ('calc', 'I16'),
    'tdpi_C':    ('calc', 'J28'),
    'mdots':     ('calc', 'D27'),
    'mdott':     ('calc', 'J29'),
}


def extract(sc: XLScenario) -> dict:
    """Run one scenario and read all intermediate values."""
    with SpreadsheetOracle() as oracle:
        oracle.run(sc)  # sets inputs and recalculates
        out = {}
        for name, (sheet, cell) in INTERMEDIATE_CELLS.items():
            try:
                out[name] = oracle._wb.sheets[sheet].range(cell).value
            except Exception as e:
                out[name] = f'ERR:{e}'
        return out


def extract_many(scenarios) -> dict:
    """Extract intermediates for several named scenarios in one Excel session."""
    out = {}
    with SpreadsheetOracle() as oracle:
        for name, sc in scenarios:
            oracle.run(sc)
            vals = {}
            for k, (sheet, cell) in INTERMEDIATE_CELLS.items():
                try:
                    vals[k] = oracle._wb.sheets[sheet].range(cell).value
                except Exception as e:
                    vals[k] = None
            out[name] = vals
    return out


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    vals = extract(XLScenario())
    print('=== Reference case (W0230) VBA solver intermediates ===\n')
    for k, v in vals.items():
        if isinstance(v, float):
            print(f'  {k:12s} = {v:.6g}')
        else:
            print(f'  {k:12s} = {v}')
