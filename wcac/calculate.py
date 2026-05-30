"""
wcac.calculate — Main calculation entry point.

Orchestrates fluid property lookups, geometry, and the two-zone solver
to produce a complete WCACResult from WCACInputs.
"""
import math
from .types import WCACInputs, WCACResult
from .models import get_model, GEOMETRY_OVERRIDES
from .geometry import build_geometry, shell_dp_kPa, TUBE_OD, TUBE_ID, SEAL_STRIP_PAIRS
from .solver import Qsolver, dPsolver, dew_point, Jtotal_both, outlet_temp, wetwall_temp
from .fluids import rho, Cp, mu, Mw, Pswater, hgwater
from .units import (F_to_C, C_to_F, UoMi_flow, psig_to_bara, psia_to_bara,
                    kPa_to_psi, Wm2K_to_Btu, fouling_imp_to_SI)
from .surface import h_tube
from .solver import h_shell


# ── Fluid code lookup ─────────────────────────────────────────────────────────

_FLUID_CODE = {
    'Air':                    'g-01',
    'Argon':                  'g-02',
    'Carbon dioxide':         'g-03',
    'Carbon monoxide':        'g-04',
    'Helium':                 'g-05',
    'Hydrogen':               'g-06',
    'Methane':                'g-07',
    'Nitrogen':               'g-08',
    'Oxygen':                 'g-09',
    'Water':                  'l-10',
    'Water/ethylene glycol':  'l-11',
    'Water/propylene glycol': 'l-12',
    'Sea water':              'l-13',
}

TUBE_MAT_K = {
    'Copper (C12200)':          339.0,
    'Admiralty brass (C44300)': 111.0,
    'Al brass (C68700)':        100.0,
    '90/10 Cu/Ni (C70600)':      45.0,
    '70/30 Cu/Ni (C71500)':      29.4,
    'Stainless (S3040*)':        15.8,
    'Stainless (S3160*)':        15.0,
}


# ── Main entry point ──────────────────────────────────────────────────────────

def calculate(inp: WCACInputs, validate_inputs: bool = False) -> WCACResult:
    """Run the WCAC heat exchanger calculation.

    This is the library's main entry point.  Pass a WCACInputs dataclass,
    receive a WCACResult dataclass.  All internal calculations are in SI;
    inputs and outputs are in the units specified in the dataclasses.

    validate_inputs: if True, raises WCACValidationError when an input would
    produce a physically meaningless result (e.g. negative pressure, glycol
    concentration outside the fitted range). Use wcac.validate() to get the
    full list of issues including non-fatal warnings. Front-ends should
    validate at the UI boundary and show warnings to the user.

    Example::

        from wcac import calculate, WCACInputs
        result = calculate(WCACInputs(model='W0230', tube_temp_in_F=250, ...))
        print(f"Q = {result.Q_Btu_h:,.0f} Btu/h")
    """
    if validate_inputs:
        from .validation import assert_valid
        assert_valid(inp)
    # ── Fluid codes ─────────────────────────────────────────────────────────
    Ftt = _FLUID_CODE.get(inp.tube_fluid, 'g-01')
    Fts = _FLUID_CODE.get(inp.shell_fluid, 'l-10')

    # ── Pressure / temperature ──────────────────────────────────────────────
    fpart = psig_to_bara(inp.tube_pressure_psig)
    fpars = 1.01325   # shell (liquid, pressure irrelevant for properties)
    if Fts in ('l-11', 'l-12'):
        fpars = inp.glycol_concentration   # reuse as concentration parameter
    tit = F_to_C(inp.tube_temp_in_F)
    tis = F_to_C(inp.shell_temp_in_F)

    # ── Fouling ─────────────────────────────────────────────────────────────
    Rft = fouling_imp_to_SI(inp.tube_fouling)
    Rfs = fouling_imp_to_SI(inp.shell_fouling)

    # ── Humidity ────────────────────────────────────────────────────────────
    P_cs = psia_to_bara(inp.suction_pressure_psia)
    T_cs = F_to_C(inp.suction_temp_F)
    Psw_suc = Pswater(T_cs)
    Pw_suc  = inp.suction_rh_pct/100 * Psw_suc
    Pw_suc  = min(Pw_suc, P_cs*1e5*0.999)
    omegai  = 18.015/Mw(Ftt) * Pw_suc / max(P_cs*1e5 - Pw_suc, 1.0)

    # ── Mass flows ───────────────────────────────────────────────────────────
    mdott, _ = UoMi_flow(inp.tube_flow_uom, inp.tube_flow,
                          Ftt, fpart, tit, omegai)
    mdots, _ = UoMi_flow(inp.shell_flow_uom, inp.shell_flow,
                          Fts, fpars, tis, 0)

    # ── Geometry ─────────────────────────────────────────────────────────────
    mg = get_model(inp.model)
    geo = build_geometry(mg, inp.bundle_type, inp.tube_design_pressure_psig)

    Dto = geo.Dto; Dti = geo.Dti
    Lt  = geo.Lt_full    # full length → dPsolver
    Act = geo.Act; Acs = geo.Acs; A = geo.A
    Jc  = geo.Jc; Jl  = geo.Jl
    SAM = inp.surface_area_margin
    kappa = getattr(inp, 'tube_roughness', 1.5e-6)

    # Wall resistance
    k_tube = TUBE_MAT_K.get(inp.tube_material, 15.8)
    Rt = (TUBE_OD/2) * math.log(TUBE_OD/TUBE_ID) / k_tube

    tubetyp = 'P' if inp.tube_type.lower().startswith('p') else 'G'
    config  = -1   # aftercooler: heat from tube gas to shell water

    # ── Run main solver ───────────────────────────────────────────────────────
    Qa = Qsolver(
        tit, tis, config, Ftt, Fts, fpart, fpars,
        mdots, mdott, omegai, Act, Acs, A, SAM,
        Rfs, Rft, Dto, Dti, Lt,
        geo.sigmat, geo.Xt, Jc, Jl, geo.A_bas,
        SEAL_STRIP_PAIRS, geo.Ntcc, geo.Ntcw, geo.Nb,
        geo.Lbe, geo.Lbc, kappa, Rt, tubetyp, geo.pattern
    )

    Q_kW   = Qa[0]
    U      = Qa[2]
    dpt_kP = Qa[4]
    t2t    = Qa[6]
    t2tw   = Qa[7]
    totw   = Qa[8]
    tmtw   = Qa[10]
    tmsw   = Qa[11]
    ht_avg = Qa[13]
    hs_avg = Qa[14]
    htmt   = Qa[15]
    LMED   = Qa[16]

    # ── Outlet temperatures ───────────────────────────────────────────────────
    tot = outlet_temp(Ftt, fpart, Q_kW, mdott, tit, tis, dpt_kP, omegai, -config)
    tos = outlet_temp(Fts, fpars,  Q_kW, mdots, tis, tit, 0, 0, config)

    # ── Condensate ────────────────────────────────────────────────────────────
    dp_arr = dPsolver(tit, tot, tmtw, Ftt, fpart, mdott/Act, Dti, Lt,
                      geo.sigmat, omegai, kappa, tubetyp, config)
    omegao = dp_arr[7]
    mdotdry = mdott / (1 + omegai)
    m_cond  = max(0, mdotdry * (omegai - omegao))
    Q_cond  = m_cond * 2468400   # W  (h_fg = 2468.4 kJ/kg, DMI convention)

    # ── Shell-side pressure drop ──────────────────────────────────────────────
    T_ms = (tis + tos) / 2
    dps_kP = shell_dp_kPa(mdots, T_ms, Fts, fpars, geo, config)

    # ── Reynolds numbers for reporting ─────────────────────────────────────────
    T_mt = (tit + tot) / 2
    Ret = mdott/Act * Dti / max(mu(Ftt, fpart, T_mt), 1e-12)
    Res = mdots/Acs * Dto  / max(mu(Fts, fpars, T_ms), 1e-12)

    # ── Effective HTCs (include fouling, as the spreadsheet D26/I26 report) ────
    # Spreadsheet "Effective HTC" cells apply fouling resistance:
    #   tube : (1/ht + Dto*Rft/Dti)^-1     shell: (1/hs + Rfs)^-1
    # ht_avg / hs_avg from the solver are the clean (fouling-free) coefficients.
    ht_eff = 1.0 / (1.0/ht_avg + Dto*Rft/Dti) if ht_avg > 0 else 0.0
    hs_eff = 1.0 / (1.0/hs_avg + Rfs)         if hs_avg > 0 else 0.0

    # ── LMTD ─────────────────────────────────────────────────────────────────
    dT1 = tit - tos; dT2 = tot - tis
    if abs(dT1)>1e-9 and abs(dT2)>1e-9 and abs(dT1/dT2)>1e-9:
        LMTD = (dT1 - dT2) / math.log(dT1/dT2)
    else:
        LMTD = abs(dT1+dT2)/2

    # ── Tube wall temperatures ────────────────────────────────────────────────
    def tw_pos(Tt, Ts):
        if ht_avg > 0 and hs_avg > 0:
            return (ht_avg*Tt + hs_avg*Ts) / (ht_avg + hs_avg)
        return (Tt + Ts) / 2
    wall_F = [
        round(C_to_F(tw_pos(tit, tis)), 1),
        round(C_to_F(tw_pos(tit*0.67+tot*0.33, tis*0.67+tos*0.33)), 1),
        round(C_to_F(tw_pos(tit*0.33+tot*0.67, tis*0.33+tos*0.67)), 1),
        round(C_to_F(tw_pos(tot, tos)), 1),
    ]

    # ── Both Bell-Delaware variants ───────────────────────────────────────────
    j_both = Jtotal_both(Res, Jc, Jl, geo.A_bas, Acs, SEAL_STRIP_PAIRS,
                         geo.Ntcc, geo.Ntcw, geo.Nb, geo.Lbe, geo.Lbc)

    # ── Dew point ─────────────────────────────────────────────────────────────
    T_dew = dew_point(Ftt, fpart, omegai)

    return WCACResult(
        Q_Btu_h          = round(Q_kW * 3412.14, 0),
        tube_out_F        = round(C_to_F(tot), 1),
        shell_out_F       = round(C_to_F(tos), 1),
        dew_point_F       = round(C_to_F(T_dew), 1),
        dP_tube_psi       = round(kPa_to_psi(dpt_kP), 2),
        dP_shell_psi      = round(kPa_to_psi(dps_kP), 2),
        condensate_lb_h   = round(m_cond * 7936.64, 1),
        condensing_Btu_h  = round(Q_cond * 3.41214, 0),   # Q_cond in W → Btu/h
        condensing_pct    = round(Q_cond / max(Q_kW*1000, 1)*100, 1),
        overall_U_btu     = round(Wm2K_to_Btu(U), 0),
        tube_HTC_btu      = round(Wm2K_to_Btu(ht_eff), 0),
        shell_HTC_btu     = round(Wm2K_to_Btu(hs_eff), 0),
        LMTD_R            = round(LMTD * 1.8, 1),
        area_ft2          = round(A * 10.7639, 1),
        tube_Re           = round(Ret, 0),
        shell_Re          = round(Res, 0),
        tube_wall_temps_F = wall_F,
        Nt                = geo.Nt,
        surface_area_margin_pct = SAM,
        Jc   = round(j_both['Jc'],   4),
        Jl   = round(j_both['Jl'],   4),
        Jb   = round(j_both['Jb'],   4),
        Jr   = round(j_both['Jr'],   4),
        Js_display    = round(j_both['Js_display'],   4),
        Js_VBA        = round(j_both['Js_VBA'],       4),
        Jtot_display  = round(j_both['Jtot_display'], 4),
        Jtot_VBA      = round(j_both['Jtot_VBA'],     4),
        Ntcc_display  = float(geo.Ntcc),
        Ntcc_raw      = round(geo.Ntcc_raw, 3),
        t2t_F  = round(C_to_F(t2t), 1),
        LMED   = round(LMED, 1),
        Q_kW   = round(Q_kW, 1),
    )
