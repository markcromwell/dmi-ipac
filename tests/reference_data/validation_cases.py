"""
validation_cases — input validation / edge-case dataset.

PURPOSE: Define the conditions the calculator SHOULD reject or flag, and the
physical boundaries beyond which results are not trustworthy. Running these
against the library shows (a) where input validation is missing and (b) where
the fluid-property correlations are used outside their fitted range.

Each case states: the input, what SHOULD happen (reject/warn/clamp), what the
library CURRENTLY does, and the engineering rationale.

Categories:
  RANGE   — fluid property correlation validity limits (from VBA comments)
  PHYSICS — physically impossible or degenerate inputs
  DOMAIN  — out-of-catalogue geometry or unsupported selections
  NUMERIC — values that cause division-by-zero or non-convergence
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationCase:
    category:    str
    name:        str
    description: str
    inputs:      dict           # overrides applied to a default WCACInputs
    expected:    str            # 'reject' | 'warn' | 'clamp' | 'compute_ok'
    rationale:   str
    source:      str = ''


# ─── Fluid property range limits (from VBA source comments) ───────────────────
# These are the documented validity ranges of the curve fits. Outside them,
# the polynomial extrapolations may be wildly wrong.

RANGE_CASES = [
    ValidationCase(
        'RANGE', 'water_below_freezing',
        'Shell water inlet at -5°F (below 0°C freezing)',
        {'shell_fluid': 'Water', 'shell_temp_in_F': -5},
        'reject',
        'Water property fits valid 0.01-300°C (Rogers & Mayhew). Below 0°C '
        'water is ice; correlation extrapolates nonsensically.',
        'VBA rho_water comment: valid 0.01°C to 300°C'),
    ValidationCase(
        'RANGE', 'air_above_425C',
        'Tube air inlet at 900°F (482°C, above 425°C fit limit)',
        {'tube_fluid': 'Air', 'tube_temp_in_F': 900},
        'warn',
        'Air fits valid -100 to 425°C (Rogers & Mayhew). 482°C extrapolates '
        'Cp/k/mu polynomials beyond fitted data.',
        'VBA rho_air comment: valid -100°C to 425°C'),
    ValidationCase(
        'RANGE', 'air_below_minus100C',
        'Tube air at -200°F (-129°C, below -100°C limit)',
        {'tube_fluid': 'Air', 'tube_temp_in_F': -200},
        'warn',
        'Air fits valid from -100°C. -129°C is below fitted range.',
        'VBA rho_air comment: valid -100°C to 425°C'),
    ValidationCase(
        'RANGE', 'seawater_above_120C',
        'Sea water at 260°F (127°C, above 120°C limit)',
        {'shell_fluid': 'Sea water', 'shell_temp_in_F': 260},
        'warn',
        'Sea water fits valid 10-120°C (HEDH/ESDU). Above 120°C extrapolates.',
        'VBA rhosea comment: valid 10°C to 120°C'),
    ValidationCase(
        'RANGE', 'glycol_conc_too_low',
        'Ethylene glycol at 10% (below 20% fit minimum)',
        {'shell_fluid': 'Water/ethylene glycol', 'glycol_concentration': 10},
        'reject',
        'Glycol fits valid 20-60% vol. 10% indexes outside the lookup arrays '
        '(negative array index in VBA → wrong/garbage result).',
        'VBA rho_weg comment: valid 20% <= c <= 60%'),
    ValidationCase(
        'RANGE', 'glycol_conc_too_high',
        'Propylene glycol at 70% (above 60% fit maximum)',
        {'shell_fluid': 'Water/propylene glycol', 'glycol_concentration': 70},
        'reject',
        'Glycol fits valid 20-60% vol. 70% extrapolates beyond the highest '
        'tabulated concentration.',
        'VBA rho_wpg comment: valid 20% <= c <= 60%'),
    ValidationCase(
        'RANGE', 'glycol_below_freeze_point',
        'EG 30% at -20°F (below the solution freeze point ~-13°C)',
        {'shell_fluid': 'Water/ethylene glycol', 'glycol_concentration': 30,
         'shell_temp_in_F': -20},
        'warn',
        'EG 30% minimum temperature is -10°C (tmin_weg). At -29°C the solution '
        'would be frozen/slush; fit invalid.',
        'VBA tmin_weg lookup'),
]

# ─── Physically impossible / degenerate inputs ───────────────────────────────

PHYSICS_CASES = [
    ValidationCase(
        'PHYSICS', 'tube_colder_than_shell',
        'Tube gas inlet 60°F, shell water inlet 70°F (gas colder than coolant)',
        {'tube_temp_in_F': 60, 'shell_temp_in_F': 70},
        'warn',
        'An aftercooler COOLS hot gas with cold water. If the gas is colder '
        'than the water, heat flows backwards (config sign flips). The '
        'spreadsheet may still compute but the result is non-physical for an '
        'aftercooler use-case.',
        'Engineering: aftercooler requires T_gas_in > T_water_in'),
    ValidationCase(
        'PHYSICS', 'equal_inlet_temps',
        'Tube and shell both at 70°F (zero driving force, LMTD → 0/0)',
        {'tube_temp_in_F': 70, 'shell_temp_in_F': 70},
        'warn',
        'Equal inlet temperatures → no heat transfer, LMTD numerator and '
        'denominator both → 0. Solver must handle the degenerate case without '
        'NaN/divide-by-zero.',
        'Numerical: LMTD = (dT1-dT2)/ln(dT1/dT2) indeterminate'),
    ValidationCase(
        'PHYSICS', 'zero_tube_flow',
        'Compressor suction flow = 0 Acfm',
        {'tube_flow': 0},
        'reject',
        'Zero gas flow → zero mass velocity → Reynolds = 0 → HTC correlations '
        'divide by zero. No heat exchanger operates at zero flow.',
        'Numerical: Gt = mdot/Act = 0 breaks Re'),
    ValidationCase(
        'PHYSICS', 'zero_shell_flow',
        'Shell water flow = 0 USgpm',
        {'shell_flow': 0},
        'reject',
        'Zero coolant flow → shell outlet temperature unbounded, Re_s = 0.',
        'Numerical: Gs = mdot/Acs = 0'),
    ValidationCase(
        'PHYSICS', 'negative_flow',
        'Negative shell flow',
        {'shell_flow': -60},
        'reject',
        'Negative flow is meaningless; should be rejected at input.',
        'Engineering: flow >= 0'),
    ValidationCase(
        'PHYSICS', 'rh_over_100',
        'Suction relative humidity = 150%',
        {'suction_rh_pct': 150},
        'reject',
        'Relative humidity cannot exceed 100% (supersaturation). Would compute '
        'a specific humidity higher than saturation.',
        'Physics: 0 <= RH <= 100'),
    ValidationCase(
        'PHYSICS', 'negative_pressure',
        'Tube inlet pressure = -5 psig (absolute < 0)',
        {'tube_pressure_psig': -20},
        'reject',
        'Gauge pressure -20 psig = -5.3 psia = negative absolute pressure, '
        'physically impossible. Density would go negative.',
        'Physics: P_absolute > 0'),
]

# ─── Domain / catalogue limits ────────────────────────────────────────────────

DOMAIN_CASES = [
    ValidationCase(
        'DOMAIN', 'unknown_model',
        'Model code W9999 (not in catalogue)',
        {'model': 'W9999'},
        'reject',
        'Only W0035-W5000 exist. Unknown code must raise a clear error, not '
        'silently produce garbage.',
        'Catalogue: 34 standard models'),
    ValidationCase(
        'DOMAIN', 'negative_fouling',
        'Negative tube fouling resistance',
        {'tube_fouling': -0.001},
        'reject',
        'Fouling resistance is additive thermal resistance; cannot be negative.',
        'Physics: Rf >= 0'),
    ValidationCase(
        'DOMAIN', 'sam_over_100',
        'Surface area margin = 120%',
        {'surface_area_margin': 120},
        'warn',
        'SAM > 100% means A_eff = A/(1+1.2) — over-margining. Likely a data '
        'entry error (e.g. 120 instead of 12).',
        'Engineering: typical SAM 0-50%'),
]

# ─── Numerical edge cases (should compute but test robustness) ────────────────

NUMERIC_CASES = [
    ValidationCase(
        'NUMERIC', 'tiny_flow',
        'Very small suction flow (50 Acfm in a large W5000)',
        {'model': 'W5000', 'tube_flow': 50},
        'compute_ok',
        'Hugely oversized HX, laminar shell flow. Solver should converge to a '
        'near-zero approach temperature without failing.',
        'Robustness: laminar/low-Re branch'),
    ValidationCase(
        'NUMERIC', 'huge_flow',
        'Very large suction flow (8000 Acfm in a small W0035)',
        {'model': 'W0035', 'tube_flow': 8000},
        'compute_ok',
        'Massively undersized HX, huge pressure drop. Solver should converge '
        '(possibly with very high dP) without overflow.',
        'Robustness: high-velocity branch'),
    ValidationCase(
        'NUMERIC', 'near_saturation_inlet',
        'Saturated gas inlet (100% RH, low temperature)',
        {'suction_rh_pct': 100, 'tube_temp_in_F': 100, 'shell_temp_in_F': 60},
        'compute_ok',
        'Gas enters near its dew point — almost the whole tube condenses. Tests '
        'the wet-zone solver at the dry-zone-vanishing limit.',
        'Robustness: t2t -> tit boundary'),
]


ALL_CASES = RANGE_CASES + PHYSICS_CASES + DOMAIN_CASES + NUMERIC_CASES


def run_report():
    """Run each validation case through the library and report behaviour."""
    import sys, os
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from wcac import calculate, WCACInputs

    print('\n=== INPUT VALIDATION / EDGE-CASE AUDIT ===\n')
    print('Shows what the library CURRENTLY does for each case it SHOULD guard.\n')

    by_cat = {}
    for c in ALL_CASES:
        by_cat.setdefault(c.category, []).append(c)

    gaps = []
    for cat, cases in by_cat.items():
        print(f'\n--- {cat} ---')
        for c in cases:
            try:
                r = calculate(WCACInputs(**c.inputs))
                # Did it produce a finite, plausible result?
                import math
                q = r.Q_Btu_h
                finite = isinstance(q, (int, float)) and math.isfinite(q)
                if c.expected in ('reject',):
                    behaviour = f'COMPUTED Q={q:,.0f} (no guard)' if finite else 'produced non-finite'
                    gap = finite  # should have rejected but didn't
                elif c.expected == 'warn':
                    behaviour = f'computed Q={q:,.0f} (no warning emitted)'
                    gap = True
                else:  # clamp / compute_ok
                    behaviour = f'computed Q={q:,.0f}' if finite else 'FAILED to compute'
                    gap = not finite
            except Exception as e:
                behaviour = f'raised {type(e).__name__}: {str(e)[:50]}'
                gap = (c.expected not in ('reject',))  # raising is OK for reject
            flag = 'GAP ' if gap else 'ok  '
            if gap:
                gaps.append(c)
            print(f'  [{flag}] {c.name:26s} expect={c.expected:10s} -> {behaviour}')

    print(f'\n{"="*70}')
    print(f'{len(gaps)} validation gaps (cases where the library does not yet')
    print(f'enforce the expected reject/warn behaviour).')
    print('\nThese define the input-validation layer to add at the API/UI boundary.')
    print('The core solver intentionally computes whatever it is given; validation')
    print('belongs in a wrapper so every front-end (CLI, web, desktop) shares it.')
    return gaps


if __name__ == '__main__':
    run_report()
