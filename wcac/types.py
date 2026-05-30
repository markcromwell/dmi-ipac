"""
wcac.types — Input and output dataclasses for the WCAC calculator.

Using dataclasses with defaults matching the spreadsheet reference case
(W0230, Air 250°F, Water 70°F) so a minimal call just overrides what differs.
"""
from dataclasses import dataclass, field
from typing import Optional


# ─── Inputs ───────────────────────────────────────────────────────────────────

@dataclass
class WCACInputs:
    """All inputs to the WCAC heat exchanger calculation.

    Units follow the spreadsheet (US customary for temperatures and pressures,
    user-selectable for flow rates).  The library converts internally to SI.
    """
    # ── Aftercooler model ──────────────────────────────────────────────────
    model: str = 'W0230'
    bundle_type: str = 'Fixed'          # 'Fixed' or 'Removable'
    tube_type: str = 'Std groove'       # 'Std groove' or 'Plain'
    tube_material: str = 'Stainless (S3040*)'
    tube_design_pressure_psig: float = 300  # for tubesheet thickness selection

    # ── Tube side (compressed gas) ─────────────────────────────────────────
    tube_fluid: str = 'Air'
    tube_pressure_psig: float = 150
    tube_temp_in_F: float = 250.0
    tube_flow: float = 1423.0
    tube_flow_uom: str = 'Scfm'         # see units.py for valid options
    tube_fouling: float = 0.0           # R·ft²·h/Btu

    # ── Shell side (cooling water) ─────────────────────────────────────────
    shell_fluid: str = 'Water'
    shell_temp_in_F: float = 70.0
    shell_flow: float = 60.0
    shell_flow_uom: str = 'USgpm'
    shell_fouling: float = 0.0          # R·ft²·h/Btu
    glycol_concentration: float = 40.0  # % vol, for EG/PG fluids

    # ── Compressor suction (for dew point / humidity) ──────────────────────
    suction_pressure_psia: float = 14.7
    suction_temp_F: float = 85.0
    suction_rh_pct: float = 36.0        # relative humidity %

    # ── Performance ────────────────────────────────────────────────────────
    surface_area_margin: float = 0.0    # %


# ─── Outputs ──────────────────────────────────────────────────────────────────

@dataclass
class WCACResult:
    """All outputs from the WCAC heat exchanger calculation.

    All temperatures in °F, pressures in psi, flow in lb/h, heat in Btu/h,
    HTC in Btu/(h·ft²·R).  Both 'display' and 'VBA-internal' variants are
    provided for the four quantities documented in CALCULATION_DISCREPANCIES.md.
    """
    # ── Primary heat transfer results ─────────────────────────────────────
    Q_Btu_h:        float  = 0.0   # total heat transfer
    tube_out_F:     float  = 0.0   # tube-side outlet temperature
    shell_out_F:    float  = 0.0   # shell-side outlet temperature
    dew_point_F:    float  = 0.0   # dew point at tube inlet

    # ── Pressure drops ─────────────────────────────────────────────────────
    dP_tube_psi:    float  = 0.0
    dP_shell_psi:   float  = 0.0

    # ── Condensation ───────────────────────────────────────────────────────
    condensate_lb_h:  float = 0.0
    condensing_Btu_h: float = 0.0
    condensing_pct:   float = 0.0  # % of total heat

    # ── HTC and performance ────────────────────────────────────────────────
    overall_U_btu:   float = 0.0   # overall HTC, Btu/(h·ft²·R)
    tube_HTC_btu:    float = 0.0   # tube-side effective HTC
    shell_HTC_btu:   float = 0.0   # shell-side effective HTC
    LMTD_R:          float = 0.0   # log-mean temperature difference, °R
    area_ft2:        float = 0.0   # heat transfer surface area

    # ── Reynolds numbers ───────────────────────────────────────────────────
    tube_Re:         float = 0.0
    shell_Re:        float = 0.0

    # ── Tube wall temperatures (4 axial positions) ─────────────────────────
    tube_wall_temps_F: list = field(default_factory=list)

    # ── Geometry ───────────────────────────────────────────────────────────
    Nt:              int   = 0     # tube count
    surface_area_margin_pct: float = 0.0

    # ── Bell-Delaware correction factors (display values, see CALCULATION_DISCREPANCIES.md) ──
    Jc:   float = 0.0
    Jl:   float = 0.0
    Jb:   float = 0.0
    Jr:   float = 0.0
    Js_display: float = 0.0  # geometry sheet F40 formula: Nb/((Nb-1)+Lbe/Lbc)
    Js_VBA:     float = 0.0  # VBA Jtotal formula: ((Nb-1)+2x^0.4)/((Nb-1)+2x)
    Jtot_display: float = 0.0
    Jtot_VBA:     float = 0.0

    # ── Ntcc variants ──────────────────────────────────────────────────────
    Ntcc_display: float = 0.0  # rounded to integer (geometry sheet F16)
    Ntcc_raw:     float = 0.0  # raw Bell-Delaware formula

    # ── Solver diagnostics ─────────────────────────────────────────────────
    t2t_F:  float = 0.0   # dry/wet zone boundary temperature, °F
    LMED:   float = 0.0   # enthalpy-based mean driving force, J/kg
    Q_kW:   float = 0.0
