"""
wcac — DMI IPAC / WCAC Heat Exchanger Calculation Library
==========================================================

Faithful Python port of the W1279 DMI WCAC Design Program I0-1.xlsm
(original program ~1975, current revision I0-1, 2025-05-29).

Proprietary engineering IP of Diversified Manufacturing Inc., Lockport NY.

Quick start::

    from wcac import calculate, WCACInputs

    result = calculate(WCACInputs(
        model='W0230',
        tube_fluid='Air',
        tube_pressure_psig=150,
        tube_temp_in_F=250,
        tube_flow=1423,
        tube_flow_uom='Scfm',
        shell_fluid='Water',
        shell_temp_in_F=70,
        shell_flow=60,
        shell_flow_uom='USgpm',
        suction_pressure_psia=14.7,
        suction_temp_F=85,
        suction_rh_pct=36,
    ))

    print(f"Q           = {result.Q_Btu_h:>10,.0f} Btu/h  (spreadsheet: 292,245)")
    print(f"Tube outlet = {result.tube_out_F:>10.1f} °F     (spreadsheet: 93.6)")
    print(f"Shell outlet= {result.shell_out_F:>10.1f} °F     (spreadsheet: 79.8)")
    print(f"dP tube     = {result.dP_tube_psi:>10.2f} psi    (spreadsheet: 9.06)")
    print(f"dP shell    = {result.dP_shell_psi:>10.2f} psi    (spreadsheet: 7.55)")
    print(f"Condensate  = {result.condensate_lb_h:>10.1f} lb/h   (spreadsheet: 39.3)")

Reference case accuracy (W0230, Air 250°F/150 psig, Water 70°F/60 USgpm):
  All outputs within 1.1% of the spreadsheet.

See CALCULATION_DISCREPANCIES.md for documentation of the four places where
the spreadsheet's display cells and VBA engine use different formulas, and
which variant this library uses (defaults to display values).
"""
from .types     import WCACInputs, WCACResult
from .calculate import calculate
from .models    import get_model, list_models, ModelGeometry, GEOMETRY_OVERRIDES
from .geometry  import build_geometry, BundleGeometry, shell_dp_kPa
from .fluids    import (rho, Cp, K, mu, Pr, Mw,
                        Pswater, hgwater, hfwater)
from .solver    import (dew_point, outlet_temp, wetwall_temp,
                        h_shell,
                        Jtotal, Jtotal_both, tubewall, dPsolver,
                        QsolverSP, Qsolver)
from .surface   import (fcp_plaintube, Nu_plaintube, h_tube, f_tube,
                        f_shell, j_shell, KcKe)
from .units     import (F_to_C, C_to_F, UoMi_flow, UoMo_flow,
                        UoMi_press, UoMo_press,
                        psig_to_bara, psia_to_bara, kPa_to_psi,
                        Wm2K_to_Btu, fouling_imp_to_SI)

__version__ = '1.0.0'
__author__  = 'Diversified Manufacturing Inc.'

__all__ = [
    # Primary API
    'calculate', 'WCACInputs', 'WCACResult',
    # Model table
    'get_model', 'list_models', 'ModelGeometry', 'GEOMETRY_OVERRIDES',
    # Geometry
    'build_geometry', 'BundleGeometry', 'shell_dp_kPa',
    # Solver (Module 3)
    'Qsolver', 'QsolverSP', 'dPsolver', 'tubewall',
    'Jtotal', 'Jtotal_both',
    'dew_point', 'outlet_temp', 'wetwall_temp', 'h_shell',
    # Surface correlations (Module 2)
    'h_tube', 'f_tube', 'f_shell', 'j_shell', 'KcKe',
    'fcp_plaintube', 'Nu_plaintube',
    # Fluid properties (Module 1)
    'rho', 'Cp', 'K', 'mu', 'Pr', 'Mw',
    'Pswater', 'hgwater', 'hfwater',
    # Unit conversions (Module 4)
    'F_to_C', 'C_to_F',
    'UoMi_flow', 'UoMo_flow', 'UoMi_press', 'UoMo_press',
    'psig_to_bara', 'psia_to_bara', 'kPa_to_psi',
    'Wm2K_to_Btu', 'fouling_imp_to_SI',
]
