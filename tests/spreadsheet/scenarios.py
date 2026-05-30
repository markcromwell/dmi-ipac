"""
scenarios — comprehensive test matrix for spreadsheet-vs-library validation.

Each scenario exercises a different part of the calculation:
  - models across the size range
  - different gases and shell fluids
  - high/low pressure, temperature, flow
  - dry (no condensation) vs heavily condensing
  - different tube materials and types
  - fouling, surface area margin
  - multiple flow-rate units
"""
from .xl_driver import XLScenario


def reference():
    """The canonical W0230 reference case from the spreadsheet sample data."""
    return XLScenario()


def all_scenarios():
    """Return a list of (name, XLScenario) covering the calculation space."""
    s = []

    # ── 1. Reference case ──────────────────────────────────────────────────
    s.append(('reference_W0230', XLScenario()))

    # ── 2. Model size sweep (same conditions, different geometry) ───────────
    for model in ['W0035', 'W0045', 'W0110', 'W0230', 'W0490',
                  'W0710', 'W1400', 'W2000', 'W5000']:
        s.append((f'model_{model}', XLScenario(
            model=model,
            suction_flow=300 if model < 'W0200' else 1500,
        )))

    # ── 3. Tube inlet temperature sweep ────────────────────────────────────
    for T in [150, 200, 250, 300, 350, 400]:
        s.append((f'tube_temp_{T}F', XLScenario(tube_temp_in_F=T)))

    # ── 4. Tube inlet pressure sweep ───────────────────────────────────────
    for P in [50, 100, 150, 200, 300]:
        s.append((f'tube_press_{P}psig', XLScenario(tube_pressure_psig=P)))

    # ── 5. Shell water temperature sweep (affects condensation) ────────────
    for T in [50, 60, 70, 85, 100]:
        s.append((f'shell_temp_{T}F', XLScenario(shell_temp_in_F=T)))

    # ── 6. Suction flow sweep ──────────────────────────────────────────────
    for F in [800, 1200, 1500, 2000, 2500]:
        s.append((f'suction_flow_{F}acfm', XLScenario(suction_flow=F)))

    # ── 7. Shell water flow sweep ──────────────────────────────────────────
    for F in [30, 45, 60, 90, 120]:
        s.append((f'shell_flow_{F}gpm', XLScenario(shell_flow=F)))

    # ── 8. Humidity sweep (condensation driver) ────────────────────────────
    for rh in [0, 20, 36, 60, 90]:
        s.append((f'humidity_{rh}pct', XLScenario(suction_rh_pct=rh)))

    # ── 9. Dry case (low humidity, hot water → no condensation) ─────────────
    s.append(('dry_no_condensation', XLScenario(
        suction_rh_pct=5, shell_temp_in_F=100, tube_temp_in_F=300)))

    # ── 10. Heavily condensing (high humidity, cold water) ──────────────────
    s.append(('heavy_condensation', XLScenario(
        suction_rh_pct=90, shell_temp_in_F=50, tube_temp_in_F=250)))

    # ── 11. Different gases ─────────────────────────────────────────────────
    for gas in ['Air', 'Nitrogen', 'Oxygen', 'Carbon dioxide',
                'Argon', 'Methane', 'Hydrogen', 'Helium', 'Carbon monoxide']:
        s.append((f'gas_{gas.replace(" ","_")}', XLScenario(tube_fluid=gas)))

    # ── 12. Different shell fluids ─────────────────────────────────────────
    s.append(('shell_seawater', XLScenario(shell_fluid='Sea water')))
    s.append(('shell_EG40', XLScenario(
        shell_fluid='Water/ethylene glycol', shell_glycol_conc=40)))
    s.append(('shell_PG40', XLScenario(
        shell_fluid='Water/propylene glycol', shell_glycol_conc=40)))

    # ── 13. Tube materials ─────────────────────────────────────────────────
    for mat in ['Copper (C12200)', 'Admiralty brass (C44300)',
                '90/10 Cu/Ni (C70600)', '70/30 Cu/Ni (C71500)',
                'Stainless (S3040*)', 'Stainless (S3160*)']:
        s.append((f'material_{mat.split()[0]}', XLScenario(tube_material=mat)))

    # ── 14. Tube type: plain vs grooved ────────────────────────────────────
    s.append(('tube_plain', XLScenario(tube_type='Plain')))
    s.append(('tube_grooved', XLScenario(tube_type='Std groove')))

    # ── 15. Bundle type ────────────────────────────────────────────────────
    s.append(('bundle_removable', XLScenario(bundle_type='Removable')))

    # ── 16. Fouling ─────────────────────────────────────────────────────────
    s.append(('fouling_tube', XLScenario(tube_fouling=0.001)))
    s.append(('fouling_shell', XLScenario(shell_fouling=0.001)))
    s.append(('fouling_both', XLScenario(tube_fouling=0.0005, shell_fouling=0.0005)))

    # ── 17. Surface area margin ────────────────────────────────────────────
    for sam in [10, 25, 50]:
        s.append((f'SAM_{sam}pct', XLScenario(surface_area_margin=sam)))

    # ── 18. Flow rate unit variants (same physical flow) ────────────────────
    s.append(('flow_scfm', XLScenario(suction_flow=1423, suction_flow_uom='Scfm')))
    s.append(('flow_lbmin', XLScenario(suction_flow=108, suction_flow_uom='lb/min')))
    s.append(('shell_flow_lbmin', XLScenario(shell_flow=500, shell_flow_uom='lb/min')))

    return s


# Quick-validation subset (fast, ~6 scenarios) for CI / dev
def quick_scenarios():
    return [
        ('reference_W0230', XLScenario()),
        ('model_W0490', XLScenario(model='W0490')),
        ('gas_Nitrogen', XLScenario(tube_fluid='Nitrogen')),
        ('dry_no_condensation', XLScenario(
            suction_rh_pct=5, shell_temp_in_F=100, tube_temp_in_F=300)),
        ('heavy_condensation', XLScenario(
            suction_rh_pct=90, shell_temp_in_F=50)),
        ('shell_seawater', XLScenario(shell_fluid='Sea water')),
    ]
