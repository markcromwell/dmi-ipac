"""
wcac.geometry — Bundle geometry calculations.

Computes all geometry parameters needed by the Qsolver from the raw
model table data.  Also calculates shell-side pressure drop (which
lives in spreadsheet cell formulas, not in the VBA).
"""
import math
from dataclasses import dataclass
from .models import ModelGeometry, GEOMETRY_OVERRIDES
from .fluids import rho, mu, K, Pr
from .surface import f_shell


# Tube dimensions (fixed for all DMI IPAC models)
TUBE_OD = 0.012700   # m  (0.500")
TUBE_ID = 0.010922   # m  (0.430")
TUBE_ROUGHNESS = 1.5e-6  # m (smooth tube default)
BAFFLE_THICKNESS = 0.0625 * 0.0254   # m (1/16" = AA column value)
SEAL_STRIP_PAIRS = 0   # default


@dataclass
class BundleGeometry:
    """All computed geometry parameters in SI units."""
    # ── Tube bundle ──────────────────────────────────────────────────────
    Nt:        int     # tube count
    Xr:        float   # row pitch
    r_ctl:     float   # outer tube centre limit radius
    Lt_full:   float   # full tube length (used in dPsolver)
    Lt_eff:    float   # effective tube length (heat transfer area)
    A:         float   # heat transfer surface area, m²
    Act:       float   # tube-side free flow area, m²
    sigmat:    float   # tube-side porosity (for KcKe)

    # ── Shell-side flow ──────────────────────────────────────────────────
    Acs:       float   # shell-side crossflow area
    A_m_raw:   float   # unscaled crossflow area (for r_bp)
    Lbc:       float   # design central baffle gap (Acs / flow calculations)
    Lbc_std:   float   # standard central baffle gap (Lbe calculation)
    Lbe:       float   # end zone baffle gap
    Nb:        int     # number of baffles

    # ── Bell-Delaware geometry ───────────────────────────────────────────
    Fw:        float   # fraction of tubes in window
    Fc:        float   # fraction of tubes in crossflow
    theta_DS:  float   # baffle-cut angle at shell wall (rad)
    theta_ctl: float   # baffle-cut angle at outer tube CL (rad)
    Ntcc:      float   # rows in crossflow (rounded, display formula)
    Ntcc_raw:  float   # rows in crossflow (unrounded, raw formula)
    Ntcw:      float   # rows in window
    Jc:        float   # segmental baffle correction
    Jl:        float   # baffle leakage correction (exp(-2.6·r_lm))

    # ── Leakage / bypass areas ───────────────────────────────────────────
    A_sb:      float   # shell-to-baffle bypass area
    A_bt:      float   # baffle-to-tube bypass area
    A_bas:     float   # bundle-to-shell bypass area
    xi_SB:     float   # shell-to-baffle radial clearance
    xi_BT:     float   # baffle-to-tube radial clearance

    # ── Window / nozzle areas ─────────────────────────────────────────────
    A_cw:      float   # window flow area
    A_cse:     float   # end-zone crossflow area
    A_csn:     float   # shell nozzle flow area
    D_hw:      float   # window hydraulic diameter

    # ── Geometry pass-through ────────────────────────────────────────────
    Dto:       float   # tube OD
    Dti:       float   # tube ID
    Dsi:       float
    Dsn:       float
    Xt:        float
    pattern:   str
    Dbaffle:   float
    Bcut_cl:   float
    Dhole:     float
    OTL:       float
    ts_geom:   float   # tubesheet thickness used for Lt_eff


def build_geometry(mg: ModelGeometry,
                   bundle_type: str = 'Fixed',
                   dp_psig: float = 300) -> BundleGeometry:
    """Compute all bundle geometry parameters from a ModelGeometry.

    bundle_type: 'Fixed' or 'Removable'
    dp_psig:     design pressure for tubesheet thickness selection

    Applies verified overrides from GEOMETRY_OVERRIDES where available.
    See CALCULATION_DISCREPANCIES.md for explanation of the three Lbc values
    and two ts values used for different calculations.
    """
    Dto = TUBE_OD; Dti = TUBE_ID; I = 0.0254
    Dsi = mg.Dsi; Dsn = mg.Dsn; Xt = mg.Xt; OTL = mg.OTL
    Dbaffle = mg.Dbaffle; Bcut_cl = mg.Bcut_cl; Dhole = mg.Dhole
    Lbc_std = mg.Lbc_std
    N_rows = mg.N_rows; Nt_miss = mg.Nt_miss; first_row = mg.first_row
    cv_off = mg.cv_offset

    # ── Tubesheet thickness ────────────────────────────────────────────────
    ovr = GEOMETRY_OVERRIDES.get(mg.code)
    if ovr:
        ts_geom, ts_lbe, design_lbc = ovr
    else:
        dp = round(dp_psig / 100) * 100
        if dp not in (200, 300): dp = 300
        is_fixed = bundle_type.lower().startswith('f')
        ts_raw = (mg.ts_200f if dp == 200 else mg.ts_300f) if is_fixed \
                 else (mg.ts_200r if dp == 200 else mg.ts_300r)
        ts_geom = min(ts_raw, mg.Lt * 0.15)   # guard against sentinel 1000
        ts_lbe = ts_geom
        design_lbc = Lbc_std

    # ── Baffle count ────────────────────────────────────────────────────────
    Nb = mg.Nb_fixed if bundle_type.lower().startswith('f') else mg.Nb_removable
    delta_B = BAFFLE_THICKNESS

    # ── Row pitch ───────────────────────────────────────────────────────────
    if mg.pattern == 'T':   Xr = Xt * math.sqrt(3)/2
    elif mg.pattern == 'RS': Xr = Xt / math.sqrt(2)
    else:                    Xr = Xt

    # ── Tube count (Cl method — matches geometry sheet) ─────────────────────
    r_ctl = (OTL - Dto) / 2
    y_max = (N_rows/2 - 0.5) * Xr
    top_has_centre = (first_row == 'hole')
    Nt = 0
    for idx in range(N_rows):
        yn = y_max - idx*Xr; yn2 = yn*yn; rc2 = r_ctl**2
        if yn2 > rc2: continue
        Cl = math.sqrt(rc2 - yn2) - Dto/2
        has_c = top_has_centre if idx%2==0 else (not top_has_centre)
        if Cl < 0:
            Nt += 1 if has_c else 0; continue
        Nteff = int(Cl/Xt) + (0 if has_c else 1)
        Nt += 2*Nteff + (1 if has_c else 0)
    Nt = max(1, Nt - Nt_miss)

    # ── Tube lengths ─────────────────────────────────────────────────────────
    Lt_full = mg.Lt
    Lt_eff  = Lt_full - 2*ts_geom

    # ── Areas ────────────────────────────────────────────────────────────────
    A     = math.pi * Dto * Lt_eff * Nt
    Act   = math.pi/4 * Dti**2 * Nt
    sigmat = (math.pi/4 * Dti**2) / (Xt * Xr) if mg.pattern in ('T','RS') \
             else (math.pi/4 * Dti**2) / Xt**2

    # ── Shell crossflow area (calibrated to geometry sheet) ─────────────────
    A_m_raw = design_lbc * ((Dsi-OTL) + (OTL-Dto)*(1-Dto/Xt))
    Acs = max(A_m_raw * 1.31, 1e-9)

    # ── Baffle geometry ──────────────────────────────────────────────────────
    r_shell = Dsi/2
    theta_DS  = 2*math.acos(max(-1, min(1, Bcut_cl/r_shell)))
    theta_ctl = 2*math.acos(max(-1, min(1, Bcut_cl/r_ctl)))
    Fw = (theta_ctl - math.sin(theta_ctl)) / (2*math.pi)
    Fc = 1 - 2*Fw

    # Ntcc: rounded to integer matches geometry sheet F16 (see CALCULATION_DISCREPANCIES.md)
    Ntcc_raw = (OTL - 2*Bcut_cl) / Xr
    Ntcc     = max(1.0, round(Ntcc_raw))    # display formula (integer)
    Ntcw     = 0.8 * (r_ctl - Bcut_cl) / Xr

    # ── Clearances ───────────────────────────────────────────────────────────
    xi_SB = (Dsi - Dbaffle) / 2
    xi_BT = (Dhole - Dto) / 2

    # ── Leakage areas ────────────────────────────────────────────────────────
    A_sb = xi_SB * Dsi * (2*math.pi - theta_DS) / 2
    A_bt = Nt * math.pi * Dto * xi_BT * (1 - Fw)   # no delta_B/Lbc factor
    A_bas = (Dsi - OTL) * Lbc_std   # uses std gap (standard practice)

    # ── Bell-Delaware Jc and Jl ──────────────────────────────────────────────
    r_lm = (A_sb + 0.5*A_bt) / max(Acs, 1e-9)
    r_ss = A_sb / max(A_sb + A_bt, 1e-9)
    Jc = 0.55 + 0.72*Fc
    Jl = 0.44*(1-r_ss) + (1-0.44*(1-r_ss))*math.exp(-2.6*r_lm)

    # ── End zone length ──────────────────────────────────────────────────────
    # Uses ts_lbe (not ts_geom) and Lbc_std
    Lbe = max(0.02, (Lt_full - 2*ts_lbe - Nb*delta_B - (Nb-1)*Lbc_std) / 2)

    # ── Window area ──────────────────────────────────────────────────────────
    A_cw_gross = Dsi**2/8 * (theta_DS - math.sin(theta_DS))
    Nt_w = max(1, int(round(Nt*Fw)))
    A_cw = max(1e-9, A_cw_gross - Nt_w*math.pi/4*Dto**2)

    # ── End-zone and nozzle areas ─────────────────────────────────────────────
    A_cse = max(A_m_raw * Lbe / max(design_lbc, 1e-9), 1e-9)
    A_csn = max(math.pi/4 * Dsn**2, 1e-9)

    # ── Window hydraulic diameter ─────────────────────────────────────────────
    perim_w = math.pi*Dto*Nt_w + Dsi*theta_DS/2
    D_hw = max(Dto, 4*A_cw / max(perim_w, 1e-9))

    return BundleGeometry(
        Nt=Nt, Xr=Xr, r_ctl=r_ctl, Lt_full=Lt_full, Lt_eff=Lt_eff,
        A=A, Act=Act, sigmat=sigmat,
        Acs=Acs, A_m_raw=A_m_raw, Lbc=design_lbc, Lbc_std=Lbc_std, Lbe=Lbe, Nb=Nb,
        Fw=Fw, Fc=Fc, theta_DS=theta_DS, theta_ctl=theta_ctl,
        Ntcc=Ntcc, Ntcc_raw=Ntcc_raw, Ntcw=Ntcw, Jc=Jc, Jl=Jl,
        A_sb=A_sb, A_bt=A_bt, A_bas=A_bas, xi_SB=xi_SB, xi_BT=xi_BT,
        A_cw=A_cw, A_cse=A_cse, A_csn=A_csn, D_hw=D_hw,
        Dto=Dto, Dti=Dti, Dsi=Dsi, Dsn=Dsn, Xt=Xt, pattern=mg.pattern,
        Dbaffle=Dbaffle, Bcut_cl=Bcut_cl, Dhole=Dhole, OTL=OTL, ts_geom=ts_geom,
    )


def shell_dp_kPa(mdots: float, T_ms: float,
                 Fts: str, fpars: float,
                 geo: BundleGeometry, config: int) -> float:
    """Shell-side total pressure drop, kPa.

    Implements the spreadsheet calc sheet formulas D35–D47.
    Uses VBA f_shell() for friction factor with variable-property correction.

    Variable-property correction (spreadsheet D33): (μ_bulk/μ_wall)^0.14.
    r_bp uses pure geometric ratio (Lbc cancels) per geometry sheet F43.
    See CALCULATION_DISCREPANCIES.md.
    """
    Dto=geo.Dto; Xt=geo.Xt; Acs=geo.Acs; Nb=geo.Nb
    Lbc=geo.Lbc; Lbe=geo.Lbe; Ntcc=geo.Ntcc; Ntcw=geo.Ntcw
    A_sb=geo.A_sb; A_bt=geo.A_bt; A_cw=geo.A_cw; D_hw=geo.D_hw
    A_cse=geo.A_cse; A_csn=geo.A_csn; OTL=geo.OTL; Dsi=geo.Dsi

    Gs = mdots / Acs
    rho_s = rho(Fts, fpars, T_ms)
    mu_s  = mu(Fts, fpars, T_ms)
    Re    = Gs * Dto / max(mu_s, 1e-12)

    # Variable property correction (D33)
    T_wall = min(T_ms + 20, 80)
    mu_wall = mu(Fts, fpars, T_wall)
    vp_corr = (mu_s / mu_wall) ** 0.14
    fF = f_shell(Re, Dto, Xt, geo.pattern) * vp_corr    # D34

    # Rl (geometry sheet F42)
    r_lm = (A_sb + 0.5*A_bt) / max(Acs, 1e-9)
    Rl = math.exp(-3.3 * max(r_lm, 1e-9))

    # Rb (geometry sheet F43) — pure geometric ratio, Lbc cancels
    r_bp = (Dsi - OTL) / ((Dsi - OTL) + (OTL - Dto)*(1 - Dto/Xt))
    Rb = math.exp(-3.7 * r_bp)

    # Crossflow (D35 → D36)
    dPi = 4 * fF * Gs**2 * Ntcc / (2 * rho_s)
    dPx = dPi * Rl * Rb * max(Nb-1, 1)

    # Window (D38 / D39 → D40)
    Gw = mdots / math.sqrt(max(Acs * A_cw, 1e-12))
    dPwt = Rl * (2 + 0.6*Ntcw) * Gw**2 / (2*rho_s)
    dPwl = (Rl * (26*mu_s*Gw*(Ntcw/max(Dto,1e-9) + Lbc/max(D_hw,1e-9)**2))
            / rho_s + Gw**2/rho_s)
    dPw = (dPwt*Nb if Re > 200 else dPwl*Nb if Re < 50
           else (dPwt*(Re-50)/150 + dPwl*(200-Re)/150)*Nb)

    # End zone (D41 = dPi × Rl × Rb, both end zones combined)
    dPe = dPi * Rl * Rb

    # Nozzle (D43 / D44 → D45 / D46)
    sigmaS = A_csn / max(A_cse, 1e-9)
    Gn = mdots / max(A_csn, 1e-9)
    Kc = (0.5 - 0.222*sigmaS) if sigmaS <= 0.18 else (0.55 - 0.5*sigmaS)
    Ke = (1 - sigmaS)**2
    dPn = (Kc + Ke) * Gn**2 / (2*rho_s)

    return (dPx + dPw + dPe + dPn) / 1000
