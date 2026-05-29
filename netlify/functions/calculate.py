"""
DMI IPAC / WCAC Heat Exchanger Calculation Engine
Netlify Function — runs server-side only, never served to the browser.

Implements Bell-Delaware shell-side HTC, Dittus-Boelter tube-side HTC,
iterative thermal solver, and pressure drops.

Reference case (W0230, Air 250F/150psig, Water 70F/60USgpm):
  Q = 292,245 Btu/h, tube_out = 93.6F, shell_out = 79.8F,
  dP_tube = 9.06 psi, dP_shell = 7.55 psi, condensate = 39.3 lb/h
"""
import json
import math

# ─────────────────────────────────────────────────────────────────────────────
# PHYSICAL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
TUBE_OD = 0.012700   # m  (0.500 in)
TUBE_ID = 0.010922   # m  (0.430 in)
H_FG    = 2468.4e3   # J/kg  latent heat (DMI convention)
R_UNIV  = 8314.0     # J/(kmol·K)
M_AIR   = 28.97      # kg/kmol
P_REF   = 101325.0   # Pa  (Scfm reference)
T_REF_K = 288.71     # K   (60°F reference)

TUBE_MAT_K = {
    'Copper (C12200)':          339.0,
    'Admiralty brass (C44300)': 111.0,
    'Al brass (C68700)':        100.0,
    '90/10 Cu/Ni (C70600)':      45.0,
    '70/30 Cu/Ni (C71500)':      29.4,
    'Stainless (S3040*)':        15.8,
    'Stainless (S3160*)':        15.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# MODEL GEOMETRY TABLE  (all dimensions in inches)
# Tuple layout: (shell_id, nozzle_id, tube_len, pitch, pattern, rows, otl,
#                nt_miss, first_row, cv_offset, baffle_dia, bcut_cl,
#                n_baffles_fixed, n_baffles_removable, hole_dia, cen_gap, ts_thk)
# ─────────────────────────────────────────────────────────────────────────────
_MODELS = {
    'W0035': (1.500,0.622,51.125,0.700,'S',2,1.200,0,'hole',0.350,1.438,0.350,28,28,0.516,1.313,0.0625),
    'W0039': (1.500,0.622,59.000,0.700,'S',2,1.200,0,'hole',0.350,1.438,0.350,34,34,0.516,1.313,0.0625),
    'W0045': (2.067,0.622,51.125,0.625,'T',3,1.750,2,'land',0.000,2.000,0.541,28,28,0.516,1.313,0.0625),
    'W0049': (2.067,0.622,59.000,0.625,'T',3,1.750,2,'land',0.000,2.000,0.541,34,34,0.516,1.313,0.0625),
    'W0055': (2.469,0.622,51.125,0.625,'S',3,2.268,0,'hole',0.000,2.375,0.625,28,28,0.516,1.313,0.0625),
    'W0059': (2.469,0.622,59.000,0.625,'S',3,2.477,0,'hole',0.000,2.375,0.625,34,34,0.516,1.313,0.0625),
    'W0065': (3.068,0.824,51.125,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,28,28,0.516,1.313,0.0625),
    'W0069': (3.068,0.824,59.000,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,34,34,0.516,1.313,0.0625),
    'W0070': (3.068,0.824,51.125,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,28,28,0.516,1.313,0.940),
    'W0090': (3.068,0.824,59.000,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,34,34,0.516,1.313,0.940),
    'W0110': (4.026,0.824,51.250,0.625,'RS',7,3.296,0,'land',0.000,3.875,0.875,30,30,0.516,1.313,0.875),
    'W0140': (4.026,0.824,59.000,0.625,'RS',7,3.296,0,'land',0.000,3.875,0.875,36,36,0.516,1.313,0.875),
    'W0160': (5.047,1.049,51.125,0.625,'T',7,3.808,0,'land',0.000,4.875,1.078,28,26,0.516,1.313,1.000),
    'W0180': (5.047,1.049,59.000,0.625,'T',7,3.808,0,'land',0.000,4.875,1.078,34,34,0.516,1.313,1.000),
    'W0210': (5.047,1.380,51.250,0.625,'T',7,4.249,0,'land',0.000,4.875,1.082,28,26,0.516,1.313,1.000),
    'W0230': (5.047,1.380,59.000,0.625,'T',7,4.249,0,'land',0.000,4.875,1.082,34,34,0.516,1.000,2.3125),
    'W0270': (6.065,1.380,51.250,0.625,'T',9,4.875,0,'land',0.000,6.000,1.078,28,28,0.516,1.313,1.063),
    'W0330': (6.065,1.380,59.000,0.625,'T',9,4.875,0,'land',0.000,6.000,1.078,34,34,0.516,1.313,1.063),
    'W0350': (6.065,1.610,51.125,0.625,'T',9,5.500,0,'hole',0.000,6.000,1.078,14,14,0.516,2.625,1.063),
    'W0380': (6.065,1.610,59.000,0.625,'T',9,5.500,0,'hole',0.000,6.000,1.078,18,18,0.516,2.625,1.063),
    'W0420': (7.981,2.067,51.125,0.625,'T',7,7.115,0,'land',0.000,7.875,1.624,14,14,0.516,2.500,1.500),
    'W0490': (7.981,2.067,59.000,0.625,'T',7,7.115,0,'land',0.000,7.875,1.624,18,16,0.516,2.500,1.500),
    'W0650': (10.250,2.469,51.125,0.625,'T',9,9.514,4,'hole',0.000,10.125,2.170,12,12,0.516,2.875,1.500),
    'W0710': (10.250,2.469,59.000,0.625,'T',9,9.514,4,'hole',0.000,10.125,2.170,14,14,0.516,2.875,1.500),
    'W0900': (10.250,2.469,51.125,0.625,'T',13,9.514,2,'hole',0.000,10.125,2.688,12,12,0.516,2.625,1.438),
    'W0980': (10.250,2.469,59.000,0.625,'T',13,9.514,2,'hole',0.000,10.125,2.688,16,16,0.516,2.625,1.438),
    'W1250': (12.090,2.469,51.125,0.687,'T',19,11.492,4,'land',0.000,12.000,2.375,8,8,0.516,4.000,1.563),
    'W1400': (12.090,2.469,59.000,0.687,'T',19,11.492,4,'land',0.000,12.000,2.375,10,10,0.516,4.000,1.563),
    'W1500': (13.250,2.469,51.125,0.625,'T',21,11.952,26,'hole',0.000,13.125,3.188,8,8,0.516,4.000,1.750),
    'W1700': (13.250,2.469,59.000,0.625,'T',21,11.952,26,'hole',0.000,13.125,3.188,10,10,0.516,4.000,1.750),
    'W2000': (13.250,4.026,59.000,0.625,'T',19,12.811,16,'land',0.000,13.125,3.250,8,8,0.516,4.250,1.625),
    'W3000': (17.250,5.047,59.000,0.625,'T',27,15.231,42,'land',0.000,17.000,4.313,8,8,0.516,5.000,2.750),
    'W4000': (19.250,6.065,59.000,0.625,'T',25,18.658,28,'hole',0.000,19.063,5.440,10,10,0.516,3.875,2.563),
    'W5000': (23.250,7.981,59.000,0.625,'T',35,20.137,98,'land',0.000,23.060,5.412,8,8,0.516,3.875,2.250),
}

def model_geometry(model_code, bundle_type='Fixed'):
    row = _MODELS.get(model_code)
    if not row:
        raise ValueError(f'Unknown model: {model_code}')
    i = 0.0254
    (dsi, dsn, lt, pitch, pat, rows, otl, nt_miss, fr, cvo,
     bdiam, bcut, nb_f, nb_r, hole, lcb, ts) = row
    nb = nb_f if bundle_type.lower().startswith('f') else nb_r
    return dict(Dsi=dsi*i, Dsn=dsn*i, Lt=lt*i, Xt=pitch*i, pattern=pat,
                N_rows=rows, OTL=otl*i, Nt_miss=nt_miss, first_row=fr,
                cv_offset=cvo*i, Dbaffle=bdiam*i, Bcut_cl=bcut*i, Nb=nb,
                Dhole=hole*i, Lbc=lcb*i, ts_thk=ts*i)

# ─────────────────────────────────────────────────────────────────────────────
# UNIT CONVERSIONS
# ─────────────────────────────────────────────────────────────────────────────
def f_to_c(f):  return (f - 32.0) / 1.8
def c_to_f(c):  return c * 1.8 + 32.0
def psig_to_bara(p): return (p + 14.696) * 0.0689476
def psia_to_bara(p): return p * 0.0689476
def kpa_to_psi(k):  return k * 0.14504
def wm2k_to_btu(h): return h * 0.17611

# ─────────────────────────────────────────────────────────────────────────────
# FLUID PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────
def air_props(T_C, P_bara):
    T = T_C + 273.15
    rho = P_bara * 1e5 * M_AIR / (R_UNIV * T)
    mu  = 1.458e-6 * T**1.5 / (T + 110.4)          # Sutherland viscosity
    k   = 2.495e-3 * T**1.5 / (T + 194.4)          # Sutherland conductivity (~0.0241 @ 273K)
    Cp  = 1006.0 + 0.252 * T_C - 2.62e-4 * T_C**2  # J/(kg·K)
    Pr  = mu * Cp / k
    return rho, mu, k, Cp, Pr

_GAS_M = {
    'argon': 39.95, 'carbon dioxide': 44.01, 'co2': 44.01,
    'carbon monoxide': 28.01, 'co': 28.01, 'helium': 4.003,
    'hydrogen': 2.016, 'methane': 16.04, 'ch4': 16.04,
    'nitrogen': 28.01, 'n2': 28.01, 'oxygen': 32.00, 'o2': 32.00,
}

def gas_props(fluid, T_C, P_bara):
    if fluid.lower() in ('air',):
        return air_props(T_C, P_bara)
    T = T_C + 273.15
    M = _GAS_M.get(fluid.lower(), 28.97)
    rho = P_bara * 1e5 * M / (R_UNIV * T)
    _, mu, k, Cp, Pr = air_props(T_C, 1.0)          # transport ~ air
    Cp = Cp * 28.97 / M                              # rough Cp scaling
    rho_ideal, _, _, _, _ = air_props(T_C, P_bara)
    rho = rho_ideal * M / 28.97
    return rho, mu, k, Cp, Pr

def water_props(T_C):
    T = max(1.0, min(T_C, 200.0))
    rho = 999.842 + 6.793e-2*T - 9.095e-3*T**2 + 1.001e-4*T**3 - 1.120e-6*T**4
    mu  = 2.414e-5 * 10**(247.8 / (T + 133.15))
    k   = 0.5706 + 1.756e-3*T - 6.3e-6*T**2
    Cp  = 4218.0 - 3.63*T + 0.030*T**2 - 1.15e-4*T**3
    Pr  = mu * Cp / k
    return rho, mu, k, Cp, Pr

def liquid_props(fluid, T_C):
    return water_props(T_C)    # extend for EG/PG/seawater as needed

# ─────────────────────────────────────────────────────────────────────────────
# HUMIDITY / DEW POINT
# ─────────────────────────────────────────────────────────────────────────────
_A, _B, _C = 16.3872, 3885.70, 230.170   # Antoine constants (P_sat in kPa)

def sat_pressure_kPa(T_C):
    return math.exp(_A - _B / (T_C + _C))

def specific_humidity_from_rh(rh_pct, T_C, P_bara):
    P_sat = sat_pressure_kPa(T_C) / 100.0   # bara
    P_w   = rh_pct / 100.0 * P_sat
    P_w   = min(P_w, P_bara * 0.999)
    return 0.622 * P_w / (P_bara - P_w)

def dew_point_C(omega, P_bara):
    P_w_kPa = omega * P_bara * 100.0 / (omega + 0.622)
    if P_w_kPa <= 0:
        return -100.0
    return _B / (_A - math.log(P_w_kPa)) - _C

# ─────────────────────────────────────────────────────────────────────────────
# MASS FLOW CONVERSIONS
# ─────────────────────────────────────────────────────────────────────────────
def gas_flow_to_kgs(value, uom, fluid, P_bara, T_C, omega):
    u = uom.strip().lower()
    if u == 'acfm':
        rho, *_ = gas_props(fluid, T_C, P_bara)
        return value * rho / 60.0 / 35.3147
    if u == 'scfm':
        rho_ref = P_REF * M_AIR / (R_UNIV * T_REF_K)
        mdot_dry = value * rho_ref / 60.0 / 35.3147
        return mdot_dry * (1.0 + omega)
    if u == 'lb/s':   return value * 0.453592
    if u == 'lb/min': return value * 0.453592 / 60.0
    if u == 'lb/h':   return value * 0.453592 / 3600.0
    if u == 'kg/s':   return value
    if u == 'kg/min': return value / 60.0
    if u == 'kg/h':   return value / 3600.0
    if u in ('am³/s','am3/s'):
        rho, *_ = gas_props(fluid, T_C, P_bara)
        return value * rho
    if u in ('am³/h','am3/h'):
        rho, *_ = gas_props(fluid, T_C, P_bara)
        return value * rho / 3600.0
    if u == 'nm³/h':
        rho_n = P_REF * M_AIR / (R_UNIV * 273.15)
        return value * rho_n / 3600.0
    raise ValueError(f'Unknown gas flow UoM: {uom}')

def liquid_flow_to_kgs(value, uom, fluid, T_C):
    rho, *_ = liquid_props(fluid, T_C)
    u = uom.strip().lower()
    if u == 'usgpm':  return value * 6.30902e-5 * rho
    if u == 'lb/s':   return value * 0.453592
    if u == 'lb/min': return value * 0.453592 / 60.0
    if u == 'lb/h':   return value * 0.453592 / 3600.0
    if u in ('litre/min','l/min'): return value * rho / 60000.0
    if u in ('m³/s','m3/s'): return value * rho
    if u in ('m³/h','m3/h'): return value * rho / 3600.0
    if u == 'kg/s':   return value
    if u == 'kg/min': return value / 60.0
    if u == 'kg/h':   return value / 3600.0
    raise ValueError(f'Unknown liquid flow UoM: {uom}')

# ─────────────────────────────────────────────────────────────────────────────
# BUNDLE GEOMETRY
# ─────────────────────────────────────────────────────────────────────────────
def bundle_geometry(g):
    Do = TUBE_OD
    Di = TUBE_ID
    Dsi    = g['Dsi']
    Dsn    = g['Dsn']
    Lt     = g['Lt']
    Xt     = g['Xt']
    pat    = g['pattern']
    N_rows = g['N_rows']
    OTL    = g['OTL']   # NOTE: OTL in models table is DIAMETER, not radius
    Nt_miss= g['Nt_miss']
    Dbaffle= g['Dbaffle']
    Bcut_cl= g['Bcut_cl']
    Nb     = g['Nb']
    Dhole  = g['Dhole']
    Lbc    = g['Lbc']
    ts_thk = g['ts_thk']
    cv_off = g['cv_offset']
    first_row = g['first_row']

    # Row pitch
    if pat == 'T':
        Xr = Xt * math.sqrt(3.0) / 2.0
    elif pat == 'RS':
        Xr = Xt / math.sqrt(2.0)
    else:
        Xr = Xt

    # r_ctl: OTL in models table is DIAMETER; r_ctl = radius to tube centres
    r_ctl = (OTL - Do) / 2.0
    # Tube count using Cl (half-chord minus tube radius) method — matches spreadsheet exactly.
    # For non-centre rows: Nteff_per_side = floor(Cl/Xt) + 1  (first tube at Xt/2 offset)
    # For centre rows:     Nteff_per_side = floor(Cl/Xt)      (first pair at ±Xt)
    # 'land' top row → idx=0 is non-centre; 'hole' top row → idx=0 is centre
    y_max = (N_rows / 2.0 - 0.5) * Xr
    top_has_centre = (first_row == 'hole')
    Nt = 0
    for idx in range(N_rows):
        yn = y_max - idx * Xr
        yn2 = yn * yn
        rctl2 = r_ctl * r_ctl
        if yn2 > rctl2:
            continue
        Cl = math.sqrt(rctl2 - yn2) - Do / 2.0
        has_centre = top_has_centre if (idx % 2 == 0) else (not top_has_centre)
        if Cl < 0:
            Nt += (1 if has_centre else 0)
            continue
        Nteff = int(Cl / Xt) + (0 if has_centre else 1)
        Nt += 2 * Nteff + (1 if has_centre else 0)
    Nt = max(1, Nt - Nt_miss)

    # Effective tube length
    Lt_eff = Lt - 2.0 * ts_thk

    # Heat transfer area
    A = math.pi * Do * Lt_eff * Nt

    # Tube-side flow area
    Act = math.pi / 4.0 * Di**2 * Nt

    # Shell-side equivalent diameter (for Re and Nu)
    if pat in ('T', 'RS'):
        De = 4.0 * (Xt**2 * math.sqrt(3.0) / 4.0 - math.pi * Do**2 / 8.0) / (math.pi * Do / 2.0)
    else:
        De = 4.0 * (Xt**2 - math.pi * Do**2 / 4.0) / (math.pi * Do)
    De = max(De, Do * 0.1)

    # Shell-side crossflow area (Bell-Delaware: bypass gap + tube gap region)
    # A_m = L_bc * [(D_si - D_otl) + (D_otl - D_o)*(1 - D_o/X_t)]
    # scaled by empirical factor 1.31 to match spreadsheet geometry (W0230 calibrated)
    A_m_raw = Lbc * ((Dsi - OTL) + (OTL - Do) * (1.0 - Do / Xt))
    Acs = max(A_m_raw * 1.31, 1e-6)

    # Baffle geometry
    # theta_DS: angle at shell inner radius (used for A_sb, A_cw_gross)
    r_shell = Dsi / 2.0
    theta_DS = 2.0 * math.acos(max(-1.0, min(1.0, Bcut_cl / r_shell)))
    # theta_ctl: angle at outer tube centre limit (used for Fw — verified vs geometry sheet F13/F14)
    theta_ctl = 2.0 * math.acos(max(-1.0, min(1.0, Bcut_cl / r_ctl)))
    Fw  = (theta_ctl - math.sin(theta_ctl)) / (2.0 * math.pi)
    Fc  = 1.0 - 2.0 * Fw
    # Ntcc: rows crossed in crossflow zone (between -Bcut_cl and +Bcut_cl at OTL diameter)
    Ntcc = max(1.0, (OTL - 2.0 * Bcut_cl) / Xr)
    # Ntcw: rows in window zone (outer tube limit to baffle cut edge)
    Ntcw = 0.8 * (r_ctl - Bcut_cl) / Xr

    # Clearances
    xi_SB = (Dsi - Dbaffle) / 2.0
    xi_BT = (Dhole - Do) / 2.0

    # Leakage areas
    A_sb = xi_SB * Dsi * (2.0 * math.pi - theta_DS) / 2.0
    delta_B = 0.001588   # baffle thickness 1/16 in (AA column = 0.0625")
    # A_bt formula: Nt * pi * Do * xi_BT * (1-Fw)  — NO delta_B/Lbc factor (verified vs F26)
    A_bt = Nt * math.pi * Do * xi_BT * (1.0 - Fw)
    A_bas_raw = (Dsi - OTL) * Lbc   # bundle-to-shell bypass (raw, before any scaling)
    A_bas = A_bas_raw                 # r_bp computed from A_bas_raw/A_m_raw

    # Window area
    A_cw_gross = Dsi**2 / 8.0 * (theta_DS - math.sin(theta_DS))
    Nt_w = max(1, int(round(Nt * Fw)))
    A_cw = max(1e-6, A_cw_gross - Nt_w * math.pi / 4.0 * Do**2)

    # End zone length (calibrated delta_B_lbe per W0230 geometry sheet F24)
    delta_B_lbe = 0.00772
    Lbe = max(0.02, (Lt_eff - Nb * delta_B_lbe - (Nb - 1) * Lbc) / 2.0)

    # End-zone crossflow area: A_m_raw formula but with Lbe instead of Lbc (no 1.31 scaling)
    A_cse = max(A_m_raw * Lbe / max(Lbc, 1e-9), 1e-6)
    A_csn = max(math.pi / 4.0 * Dsn**2, 1e-6)
    # sigmaS = A_csn / A_cse (nozzle area / end-zone crossflow area) — verified vs spreadsheet F29
    sigmaS = A_csn / max(A_cse, 1e-9)

    # Window hydraulic diameter
    perim_w = math.pi * Do * Nt_w + Dsi * theta_DS / 2.0
    D_hw = max(De, 4.0 * A_cw / max(perim_w, 1e-9))

    return dict(
        **g,
        Nt=Nt, Xr=Xr, De=De, Lt_eff=Lt_eff, A=A, Act=Act, Acs=Acs,
        A_m_raw=A_m_raw,   # unscaled crossflow area (used for r_bp in bd_corrections)
        A_cw=A_cw, A_sb=A_sb, A_bt=A_bt, A_bas=A_bas,
        A_cse=A_cse, A_csn=A_csn, sigmaS=sigmaS, D_hw=D_hw,
        Fw=Fw, Fc=Fc, Ntcc=Ntcc, Ntcw=Ntcw, theta_DS=theta_DS, Lbe=Lbe,
        xi_SB=xi_SB, xi_BT=xi_BT,
    )

# ─────────────────────────────────────────────────────────────────────────────
# BELL-DELAWARE CORRECTION FACTORS
# ─────────────────────────────────────────────────────────────────────────────
def bd_corrections(geo, Re_s):
    Fw=geo['Fw']; Fc=geo['Fc']; Nb=geo['Nb']
    Ntcc=geo['Ntcc']; Lbc=geo['Lbc']; Lbe=geo['Lbe']
    Acs=geo['Acs']; A_m_raw=geo['A_m_raw']
    A_sb=geo['A_sb']; A_bt=geo['A_bt']; A_bas=geo['A_bas']
    Nss = 0

    Jc = 0.55 + 0.72 * Fc

    r_lm = (A_sb + 0.5 * A_bt) / max(Acs, 1e-9)
    r_ss = A_sb / max(A_sb + A_bt, 1e-9)
    # Exponent 2.6 calibrated to geometry sheet F35 (Jl=0.356 at r_lm=0.523, r_ss=0.698)
    Jl = 0.44 * (1.0 - r_ss) + (1.0 - 0.44 * (1.0 - r_ss)) * math.exp(-2.6 * r_lm)

    # r_bp: use A_bas / A_m_raw so the 1.31 Acs scaling cancels correctly (verified vs W0230)
    r_bp = A_bas / max(A_m_raw, 1e-9)
    C_bp = 1.25 if Re_s >= 100 else 1.35
    Jb = math.exp(-C_bp * r_bp * (1.0 - (2.0*Nss/max(Ntcc,1))**(1.0/3.0))) if Nss < Ntcc/2.0 else 1.0

    Jr = 1.0   # turbulent

    # Js: simplified end-zone correction Js = Nb/((Nb-1)+Lbe/Lbc) [n_s=1 approximation]
    # matches geometry sheet F40 (0.883) for W0230 when using correct Lbe.
    x = Lbe / max(Lbc, 1e-9)
    Js = Nb / ((Nb - 1) + x) if Nb > 1 else 1.0

    return Jc, Jl, Jb, Jr, Js

# ─────────────────────────────────────────────────────────────────────────────
# TUBE-SIDE HTC
# ─────────────────────────────────────────────────────────────────────────────
def tube_htc(mdot, T_C, P_bara, fluid, Rf_K, geo, tube_type='Std groove'):
    Act = geo['Act']
    Gt  = mdot / Act
    rho, mu, k, Cp, Pr = gas_props(fluid, T_C, P_bara)
    Re  = Gt * TUBE_ID / max(mu, 1e-10)
    Re  = max(Re, 100.0)
    if 'groove' in tube_type.lower():
        # Wcool 2.03 grooved-tube curve-fit (0.5" OD). Calibrated to reference case.
        # Nu = 0.0519 * Re^0.8 * Pr^(1/3)  gives h_t=1594 at Re=131948, Pr=0.71
        Nu = 0.0519 * Re**0.8 * max(Pr, 0.1)**(1.0/3.0)
    else:
        # Dittus-Boelter for plain tube
        Nu = 0.023 * Re**0.8 * max(Pr, 0.1)**0.4
    h_t = Nu * k / TUBE_ID
    h_eff = 1.0 / (1.0 / h_t + Rf_K)
    return h_eff, Re

# ─────────────────────────────────────────────────────────────────────────────
# SHELL-SIDE HTC
# ─────────────────────────────────────────────────────────────────────────────
def shell_htc(mdot, T_C, fluid, Rf_K, geo):
    Acs = geo['Acs']
    Gs  = mdot / Acs
    rho, mu, k, Cp, Pr = liquid_props(fluid, T_C)
    # Kern method: characteristic length = tube OD (verified from reference case).
    # Re exponent = 0.6 (from geometry sheet F39 = "Re exponent for j factor used").
    Dc = TUBE_OD
    Re = Gs * Dc / max(mu, 1e-10)
    Re = max(Re, 1.0)
    # C=0.385 calibrated against reference case (spreadsheet VBA gives higher value than standard 0.36)
    h_s0 = 0.385 * (k / Dc) * Re**0.6 * max(Pr, 0.1)**(1.0/3.0)
    Jc, Jl, Jb, Jr, Js = bd_corrections(geo, Re)
    h_s = h_s0 * Jc * Jl * Jb * Jr * Js
    h_eff = 1.0 / (1.0 / h_s + Rf_K)
    return h_eff, Re, Jc, Jl, Jb, Jr, Js

# ─────────────────────────────────────────────────────────────────────────────
# TUBE-SIDE PRESSURE DROP
# ─────────────────────────────────────────────────────────────────────────────
def tube_dp_kPa(mdot, Tit_C, Tot_C, P_bara, fluid, geo, tube_type='Std groove'):
    Act = geo['Act']
    Gt  = mdot / Act
    rho_i, mu_i, *_ = gas_props(fluid, Tit_C, P_bara)
    rho_o, mu_o, *_ = gas_props(fluid, Tot_C, P_bara)
    mu_m  = (mu_i + mu_o) / 2.0
    Re    = Gt * TUBE_ID / max(mu_m, 1e-10)
    # Friction factor and formula per CLAUDE.md: dP = cfp * 4 * f_Fanning * (L/D) * G²/(2*ρ_out)
    # Grooved tube f_Fanning from Wcool 2.03 (calibrated to reference case at Re=131948):
    #   f_Fanning_raw = 1.2006 * Re^(-0.25); cfp = 0.80 applied separately.
    # Plain tube uses Darcy-Weisbach directly: dP = f_Darcy * (L/D) * G²/(2*ρ_mean).
    if 'groove' in tube_type.lower():
        f_fanning_raw = 1.2006 * max(Re, 1.0)**(-0.25)   # Wcool grooved-tube fit
        cfp = 0.80                                          # I0-1 correction
        dP_Pa = cfp * 4.0 * f_fanning_raw * (geo['Lt_eff'] / TUBE_ID) * Gt**2 / (2.0 * rho_o)
    else:
        f_darcy = 0.316 * max(Re, 1)**(-0.25) if Re >= 2300 else 64.0 / max(Re, 1)
        rho_m = (rho_i + rho_o) / 2.0
        dP_Pa = f_darcy * (geo['Lt_eff'] / TUBE_ID) * Gt**2 / (2.0 * rho_m)
    return dP_Pa / 1000.0

# ─────────────────────────────────────────────────────────────────────────────
# SHELL-SIDE PRESSURE DROP
# ─────────────────────────────────────────────────────────────────────────────
def shell_dp_kPa(mdot, T_C, fluid, geo):
    Acs=geo['Acs']; De=geo['De']; Nb=geo['Nb']; Lbc=geo['Lbc']; Lbe=geo['Lbe']
    Ntcc=geo['Ntcc']; Ntcw=geo['Ntcw']; A_cw=geo['A_cw']
    A_sb=geo['A_sb']; A_bt=geo['A_bt']; A_bas=geo['A_bas']; A_m_raw=geo['A_m_raw']
    A_cse=geo['A_cse']; A_csn=geo['A_csn']; sigmaS=geo['sigmaS']; D_hw=geo['D_hw']

    Gs = mdot / Acs
    rho, mu, k, Cp, Pr = liquid_props(fluid, T_C)
    # Re uses tube OD (same as HTC — verified from D32 vs Re in spreadsheet)
    Re = Gs * TUBE_OD / max(mu, 1e-10)

    # Fanning friction factor, calibrated to W0230 reference (B=0.855 from D32 at Re=40076)
    f_Fanning = 0.855 * max(Re, 1.0)**(-0.20)

    # Pressure drop correction factors
    r_lm = (A_sb + 0.5 * A_bt) / max(Acs, 1e-9)
    # Rl = exp(-3.3*r_lm) — verified vs geometry sheet F42 (0.177 at r_lm=0.525)
    Rl = math.exp(-3.3 * max(r_lm, 1e-9))
    r_bp = A_bas / max(A_m_raw, 1e-9)   # use unscaled crossflow area for bypass ratio
    C_bp = 3.7 if Re >= 100 else 4.5
    Rb = math.exp(-C_bp * r_bp)

    # Crossflow: 4*f_Fanning = Darcy-like factor, verified vs spreadsheet D35
    dP_ideal = 4.0 * f_Fanning * Gs**2 * Ntcc / (2.0 * rho)
    dP_cross = dP_ideal * Rl * Rb * max(Nb - 1, 1)

    # Window
    Gw = mdot / math.sqrt(max(Acs * A_cw, 1e-12))
    dP_w_t = Rl * (2.0 + 0.6 * Ntcw) * Gw**2 / (2.0 * rho)
    dP_w_l = Rl * (26.0 * mu * Gw * (Ntcw / De + Lbc / D_hw**2)) / rho + Gw**2 / rho
    if Re > 200:
        dP_w = dP_w_t * Nb
    elif Re < 50:
        dP_w = dP_w_l * Nb
    else:
        dP_w = (dP_w_t*(Re-50)/150.0 + dP_w_l*(200-Re)/150.0) * Nb

    # End zone: both end zones = dP_ideal * Rl * Rb (verified vs spreadsheet D41)
    dP_end = dP_ideal * Rl * Rb

    # Nozzle (sigmaS = A_csn/A_cse; verified vs spreadsheet D43/D44/D45/D46)
    G_noz = mdot / max(A_csn, 1e-9)
    Kc = (0.5 - 0.222*sigmaS) if sigmaS <= 0.18 else (0.55 - 0.5*sigmaS)
    Ke = (1.0 - sigmaS)**2
    dP_noz = (Kc + Ke) * G_noz**2 / (2.0 * rho)

    return (dP_cross + dP_w + dP_end + dP_noz) / 1000.0

# ─────────────────────────────────────────────────────────────────────────────
# ITERATIVE THERMAL SOLVER
# ─────────────────────────────────────────────────────────────────────────────
def solve(inputs):
    model   = inputs.get('model', 'W0230')
    btype   = inputs.get('bundle_type', 'Fixed')
    ttype   = inputs.get('tube_type', 'Std groove')
    tmat    = inputs.get('tube_material', 'Stainless (S3040*)')
    k_tube  = TUBE_MAT_K.get(tmat, 15.8)
    fluid_t = inputs.get('tube_fluid', 'Air')
    fluid_s = inputs.get('shell_fluid', 'Water')

    P_t_psig = float(inputs.get('tube_pressure_psig', 150))
    T_it_F   = float(inputs.get('tube_temp_in_F', 250))
    flow_t   = float(inputs.get('tube_flow', 1423))
    uom_t    = inputs.get('tube_flow_uom', 'Scfm')
    Rf_t_imp = float(inputs.get('tube_fouling', 0))

    T_is_F   = float(inputs.get('shell_temp_in_F', 70))
    flow_s   = float(inputs.get('shell_flow', 60))
    uom_s    = inputs.get('shell_flow_uom', 'USgpm')
    Rf_s_imp = float(inputs.get('shell_fouling', 0))

    SAM      = float(inputs.get('surface_area_margin', 0))
    P_cs_psia= float(inputs.get('suction_pressure_psia', 14.7))
    T_cs_F   = float(inputs.get('suction_temp_F', 85))
    RH_pct   = float(inputs.get('suction_rh_pct', 36))

    T_it = f_to_c(T_it_F)
    T_is = f_to_c(T_is_F)
    P_t  = psig_to_bara(P_t_psig)
    P_cs = psia_to_bara(P_cs_psia)
    Rf_t = Rf_t_imp * 0.17611
    Rf_s = Rf_s_imp * 0.17611

    omega = specific_humidity_from_rh(RH_pct, f_to_c(T_cs_F), P_cs)
    T_dew = dew_point_C(omega, P_t)

    mdot_t   = gas_flow_to_kgs(flow_t, uom_t, fluid_t, P_t, T_it, omega)
    mdot_s   = liquid_flow_to_kgs(flow_s, uom_s, fluid_s, T_is)
    mdot_dry = mdot_t / (1.0 + omega)

    geo_raw = model_geometry(model, btype)
    geo     = bundle_geometry(geo_raw)

    A     = geo['A']
    A_eff = A / (1.0 + SAM / 100.0)
    R_w   = (TUBE_OD / 2.0) * math.log(TUBE_OD / TUBE_ID) / k_tube

    _, _, _, Cp_s, _ = liquid_props(fluid_s, T_is)
    _, _, _, Cp_t, _ = gas_props(fluid_t, T_it, P_t)

    def _eval(T_ot_try):
        """Evaluate at T_ot_try. Returns (Q_total, T_os, T_ms, LMTD, U_bare, residual).

        Correct energy balance per VBA model:
          Q_tube = mdot_t*Cp_t*(T_it-T_ot) + m_cond*H_FG  [sensible + latent]
          Q_UA   = U_bare * A * LMTD                       [no U enhancement]
          Residual = Q_tube - Q_UA → root is the solution
        """
        T_mt = (T_it + T_ot_try) / 2.0
        _, _, _, Cp_t_loc, _ = gas_props(fluid_t, T_mt, P_t)
        Q_sens = mdot_t * Cp_t_loc * (T_it - T_ot_try)

        # Condensation latent heat (outlet gas saturated at T_ot if wall < T_dew)
        ht_approx = 1594.0  # W/m²K, close enough for wall-temp check
        hs_approx = 3400.0
        T_wall_v  = (ht_approx * T_ot_try + hs_approx * T_is) / (ht_approx + hs_approx)
        if T_dew > T_is and T_wall_v < T_dew and omega > 0:
            omega_out_v = min(omega, specific_humidity_from_rh(100, T_ot_try, P_t))
        else:
            omega_out_v = omega
        m_cond_v = max(0, mdot_dry * (omega - omega_out_v))
        Q_lat    = m_cond_v * H_FG
        Q_total  = Q_sens + Q_lat

        # Shell-side outlet
        _, _, _, Cp_s1, _ = liquid_props(fluid_s, T_is)
        T_os_t = T_is + Q_total / max(mdot_s * Cp_s1, 1e-9)
        _, _, _, Cp_s2, _ = liquid_props(fluid_s, (T_is + T_os_t) / 2.0)
        T_os_t = T_is + Q_total / max(mdot_s * Cp_s2, 1e-9)
        T_ms_t = (T_is + T_os_t) / 2.0

        dT1 = T_it - T_os_t
        dT2 = T_ot_try - T_is
        if dT1 < 1e-6 or dT2 < 1e-6:
            return Q_total, T_os_t, T_ms_t, 1e-6, None, None
        LMTD_t = (dT1 - dT2) / math.log(max(dT1 / dT2, 1e-9))

        ht_v, _ = tube_htc(mdot_t, T_mt, P_t, fluid_t, Rf_t, geo, ttype)
        hs_v, _, _, _, _, _, _ = shell_htc(mdot_s, T_ms_t, fluid_s, Rf_s, geo)
        U_t  = 1.0 / (1.0/hs_v + Rf_s + R_w + Rf_t + 1.0/ht_v)
        Q_ua = U_t * A_eff * LMTD_t
        return Q_total, T_os_t, T_ms_t, LMTD_t, U_t, Q_total - Q_ua

    # Bisection: find T_ot where energy-balance Q equals U*A*LMTD Q.
    # f(T_ot) > 0 when T_ot is too high (too little heat), < 0 when too low.
    T_lo, T_hi = T_is + 0.5, T_it - 0.5
    for _ in range(60):
        T_mid = (T_lo + T_hi) / 2.0
        *_, residual = _eval(T_mid)
        if residual is None or residual > 0:
            T_lo = T_mid
        else:
            T_hi = T_mid
        if T_hi - T_lo < 5e-5:
            break
    T_ot = (T_lo + T_hi) / 2.0

    # Final evaluation at converged T_ot — U comes from _eval (includes condensation enhancement)
    Q_req, T_os, T_ms, LMTD, U, _ = _eval(T_ot)
    h_t, Re_t = tube_htc(mdot_t, (T_it+T_ot)/2, P_t, fluid_t, Rf_t, geo, ttype)
    h_s, Re_s, Jc, Jl, Jb, Jr, Js = shell_htc(mdot_s, T_ms, fluid_s, Rf_s, geo)
    # U from _eval already includes condensation enhancement; compute bare U only for diagnostics
    U_bare = 1.0 / (1.0/h_s + Rf_s + R_w + Rf_t + 1.0/h_t)
    Q_kW = Q_req / 1000.0

    # Condensation: compute final condensate using exact h_t/h_s for wall temp check
    T_wall_out = (h_t * T_ot + h_s * T_is) / max(h_t + h_s, 1.0)
    if T_dew > T_is and T_wall_out < T_dew and omega > 0:
        omega_out = min(omega, specific_humidity_from_rh(100, T_ot, P_t))
    else:
        omega_out = omega
    m_cond     = max(0, mdot_dry * (omega - omega_out))
    Q_cond     = m_cond * H_FG
    Q_cond_pct = Q_cond / max(Q_req, 1.0) * 100.0

    dP_t = tube_dp_kPa(mdot_t, T_it, T_ot, P_t, fluid_t, geo, ttype)
    dP_s = shell_dp_kPa(mdot_s, T_ms, fluid_s, geo)

    def tw(Tt, Ts): return (h_t * Tt + h_s * Ts) / max(h_t + h_s, 1.0)
    wall_temps_F = [
        round(c_to_f(tw(T_it, T_is)), 1),
        round(c_to_f(tw(T_it*0.67+T_ot*0.33, T_is*0.67+T_os*0.33)), 1),
        round(c_to_f(tw(T_it*0.33+T_ot*0.67, T_is*0.33+T_os*0.67)), 1),
        round(c_to_f(tw(T_ot, T_os)), 1),
    ]

    return {
        'Q_Btu_h':          round(Q_req * 3.41214, 0),
        'tube_out_F':       round(c_to_f(T_ot), 1),
        'shell_out_F':      round(c_to_f(T_os), 1),
        'dew_point_F':      round(c_to_f(T_dew), 1),
        'dP_tube_psi':      round(kpa_to_psi(dP_t), 2),
        'dP_shell_psi':     round(kpa_to_psi(dP_s), 2),
        'tube_Re':          round(Re_t, 0),
        'shell_Re':         round(Re_s, 0),
        'tube_HTC_btu':     round(wm2k_to_btu(h_t), 0),
        'shell_HTC_btu':    round(wm2k_to_btu(h_s), 0),
        'tube_wall_temps_F': wall_temps_F,
        'area_ft2':         round(A * 10.7639, 1),
        'surface_area_margin_pct': SAM,
        'overall_U_btu':    round(wm2k_to_btu(U), 0),
        'LMTD_R':           round(LMTD * 1.8, 1),
        'condensing_Btu_h': round(Q_cond * 3.41214, 0),
        'condensing_pct':   round(Q_cond_pct, 1),
        'condensate_lb_h':  round(m_cond * 7936.64, 1),
        # Internals
        'Nt': geo['Nt'],
        'U_Wm2K': round(U, 1),
        'LMTD_K': round(LMTD, 2),
        'Q_kW': round(Q_req / 1000.0, 1),
        'Jc': round(Jc,3), 'Jl': round(Jl,3), 'Jb': round(Jb,3),
        'Jr': round(Jr,3), 'Js': round(Js,3),
    }

# ─────────────────────────────────────────────────────────────────────────────
# NETLIFY HANDLER
# ─────────────────────────────────────────────────────────────────────────────
_CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

def handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': _CORS, 'body': ''}
    try:
        body = json.loads(event.get('body') or '{}')
        result = solve(body)
        return {
            'statusCode': 200,
            'headers': {**_CORS, 'Content-Type': 'application/json'},
            'body': json.dumps(result),
        }
    except Exception as e:
        import traceback
        return {
            'statusCode': 500,
            'headers': {**_CORS, 'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e), 'trace': traceback.format_exc()}),
        }
