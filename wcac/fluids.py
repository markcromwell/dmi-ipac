"""
wcac.fluids — Fluid property functions.

Faithful translation of Module1.bas from W1279 DMI WCAC Design program I0-1.xlsm.
All polynomial coefficients taken directly from the VBA source.

Fluid codes (VBA convention):
  Gas:    g-01=Air  g-02=Ar   g-03=CO2  g-04=CO   g-05=He
          g-06=H2   g-07=CH4  g-08=N2   g-09=O2
  Liquid: l-10=Water  l-11=Water/EG  l-12=Water/PG  l-13=Sea water

All temperatures in °C, pressures in bara, properties in SI.
"""
import math


# ─── Molecular weights ────────────────────────────────────────────────────────

_MW = {1: 28.96, 2: 39.948, 3: 44.01, 4: 28.01, 5: 4.003,
       6: 2.02,  7: 16.043, 8: 28.013, 9: 31.999}


def Mw(Ft: str) -> float:
    """Molecular weight, kg/kmol.  VBA: Mw(Ft)"""
    return _MW.get(int(Ft[-2:]), 28.96)


# ─── Water (0.01–300°C, Rogers & Mayhew) ─────────────────────────────────────

def rho_water(t: float) -> float:
    """Density, kg/m³"""
    if t <= 120:
        return 1000 + 0.0095578*t - 0.0056262*t**2 + 0.000013354*t**3
    return 792.97 + 4.3331*t - 0.038282*t**2 + 0.00012268*t**3 - 0.0000001539*t**4

def Cp_water(t: float) -> float:
    """Specific heat, J/(kg·K)"""
    if t <= 25.15:  return 4221.7  - 4.263*t   + 0.15911*t**2  - 0.0021464*t**3
    if t <= 44.89:  return 4213.2  - 1.9994*t  + 0.028563*t**2
    if t <= 120:    return 4198.6  - 0.91885*t + 0.012116*t**2  - 0.000008545*t**3
    return 3091.8 + 19.231*t - 0.11065*t**2 + 0.00024882*t**3

def K_water(t: float) -> float:
    """Thermal conductivity, W/(m·K)"""
    if t <= 120:
        return 0.5688 + 0.0018959*t - 0.000008626*t**2 + 0.0000000086192*t**3
    return (595.23 + 1.3658*t - 0.0048449*t**2 - 0.0000016765*t**3
            + 0.0000000021291*t**4) * 0.001

def mu_water(t: float) -> float:
    """Dynamic viscosity, Pa·s"""
    if t <= 120:
        return (0.0017487 - 0.000053635*t + 0.0000010181*t**2
                - 0.000000011676*t**3 + 0.000000000071805*t**4
                - 1.7918e-13*t**5)
    return (769.87 - 8.1453*t + 0.040941*t**2
            - 0.000099534*t**3 + 0.000000094652*t**4) * 1e-6

def Pr_water(t: float) -> float:
    """Prandtl number"""
    if t <= 47.16:
        return (12.96 - 0.4528*t + 0.0098052*t**2
                - 0.00012467*t**3 + 0.00000068414*t**4)
    if t <= 120:
        return (10.3552 - 0.2379*t + 0.0027172*t**2
                - 0.000015588*t**3 + 0.000000035778*t**4)
    return (4.9209 - 0.054892*t + 0.00029412*t**2
            - 0.00000076479*t**3 + 0.00000000082274*t**4)

def Pswater(t: float) -> float:
    """Saturation pressure of water, Pa.  IAPWS-IF97 (2012). Valid 0–373.946°C."""
    if not (0 < t < 373.946):
        return 0.0
    xi = (273.15+t) - 0.23855557567849/(273.15+t - 650.17534844798)
    A = xi**2 + 1167.0521452767*xi - 724213.16703206
    B = -17.073846940092*xi**2 + 12020.82470247*xi - 3232555.0322333
    C = 14.91510861353*xi**2 - 4823.2657361591*xi + 405113.40542057
    return 1e5 * 10 * (2*C / (-B + (B**2 - 4*A*C)**0.5))**4

def Cpgwater(t: float) -> float:
    """Cp of saturated water vapour, J/(kg·K).  Valid 0.01–300°C."""
    return math.exp(7.533 - 0.0001017*t + 0.000005191*t**2
                    + 0.00000003669*t**3 - 0.00000000003143*t**4)

def hgwater(t: float) -> float:
    """Specific enthalpy of saturated water vapour, J/kg.  Valid 0.01–300°C."""
    return 2503000 + 1660*t + 2.465*t**2 - 0.01745*t**3

def hfwater(t: float) -> float:
    """Specific enthalpy of saturated liquid water, J/kg."""
    if t < 10:
        return 4166.81*t - 41.66
    return -1263 + 4306*t - 1.785*t**2 + 0.007925*t**3


# ─── Water/Ethylene Glycol (φ = volume %, 20–60%, 2021 ASHRAE) ───────────────

def _glycol_interp(phi, t, A, B, C=None, D=None, e=None, f=None, log10=False):
    """Piecewise linear interpolation between decile φ values."""
    phimin = 10 * int(phi / 10)
    i = phimin // 10 - 2
    def poly(k):
        v = A[k] + B[k]*t
        if C: v += C[k]*t**2
        if D: v += D[k]*t**3
        if e: v += e[k]*t**4
        if f: v += f[k]*t**5
        return v
    p1, p2 = poly(i), poly(i+1)
    if log10:
        return 0.001 * 10**((p1 - p2)/10*(phimin - phi) + p1)
    return (p1 - p2)/10*(phimin - phi) + p1

def rho_weg(phi, t):
    A=[1035.7,1051.8,1066.8,1081.1,1094.6,1094.6]
    B=[-0.24864,-0.27774,-0.30738,-0.33814,-0.36982,-0.36982]
    C=[-0.002432,-0.0024316,-0.0024322,-0.0024322,-0.0024325,-0.0024325]
    return _glycol_interp(phi,t,A,B,C)
def Cp_weg(phi, t):
    A=[3768.7,3588.6,3401,3203.4,2996.6,2996.6]
    B=[2.3,2.8367,3.3556,3.8616,4.3656,4.3656]
    return _glycol_interp(phi,t,A,B)
def k_weg(phi, t):
    A=[0.46537,0.42323,0.38634,0.35235,0.32248,0.32248]
    B=[0.0014692,0.0012086,0.00096925,0.00075705,0.00059195,0.00059195]
    C=[-0.0000066581,-0.0000052883,-0.000004135,-0.0000027201,-0.0000021225,-0.0000021225]
    D=[0.0000000035498,0.0000000015871,0.00000000040636,-0.0000000035095,-0.0000000029294,-0.0000000029294]
    return _glycol_interp(phi,t,A,B,C,D)
def mu_weg(phi, t):
    A=[0.48066,0.61817,0.76569,0.90592,1.081,1.081]
    B=[-0.015396,-0.015999,-0.017365,-0.018112,-0.019919,-0.019919]
    C=[0.00012696,0.00012626,0.00015893,0.00015788,0.00012939,0.00012939]
    D=[-0.0000007509,-0.0000010258,-0.0000015288,-0.0000016299,-0.00000067045,-0.00000067045]
    e=[0.0000000013354,0.0000000058645,0.0000000093007,0.000000011197,0.000000001735,0.000000001735]
    f=[3.7932e-12,-0.000000000015174,-0.000000000023904,-0.000000000031769,0,0]
    return _glycol_interp(phi,t,A,B,C,D,e,f,log10=True)
def Pr_weg(phi, t):  return Cp_weg(phi,t)*mu_weg(phi,t)/k_weg(phi,t)


# ─── Water/Propylene Glycol (φ = volume %, 20–60%, 2021 ASHRAE) ──────────────

def rho_wpg(phi, t):
    A=[1025.8,1036.2,1045.1,1052.7,1059,1059]
    B=[-0.28997,-0.3434,-0.39263,-0.44037,-0.48682,-0.48682]
    C=[-0.0025219,-0.0025508,-0.0025719,-0.002567,-0.0025332,-0.0025332]
    return _glycol_interp(phi,t,A,B,C)
def Cp_wpg(phi, t):
    A=[3928.9,3792.9,3635.7,3454.7,3250.3,3250.3]
    B=[2.1838,2.7515,3.3014,3.8585,4.4133,4.4133]
    return _glycol_interp(phi,t,A,B)
def k_wpg(phi, t):
    A=[0.45613,0.40923,0.36646,0.32714,0.29116,0.29116]
    B=[0.0014752,0.0012111,0.00098259,0.00076193,0.00058192,0.00058192]
    C=[-0.0000065974,-0.0000052474,-0.0000042594,-0.000003036,-0.0000021872,-0.0000021872]
    D=[0.0000000022672,0.00000000051086,0,-0.0000000024418,-0.0000000041292,-0.0000000041292]
    return _glycol_interp(phi,t,A,B,C,D)
def mu_wpg(phi, t):
    A=[0.60746,0.84959,1.0908,1.262,1.4974,1.4974]
    B=[-0.017258,-0.02083,-0.025228,-0.02553,-0.028049,-0.028049]
    C=[0.00011735,0.00014517,0.000207,0.00019379,0.00018028,0.00018028]
    D=[-0.00000054263,-0.00000061911,-0.0000011071,-0.000001077,-0.0000005914,-0.0000005914]
    e=[0.000000001176,0.0000000012373,0.0000000027871,0.0000000040806,0.00000000063291,0.00000000063291]
    f=[0,0,0,-0.000000000007841,0,0]
    return _glycol_interp(phi,t,A,B,C,D,e,f,log10=True)
def Pr_wpg(phi, t):  return Cp_wpg(phi,t)*mu_wpg(phi,t)/k_wpg(phi,t)


# ─── Sea water 35 g/kg (HEDH 1992, ESDU 77024) ───────────────────────────────

def rhosea(t):  return 1028.8 - 0.1789*t - 2.637e-3*t**2
def Cpsea(t):   return 3992 - 5.033e-2*t + 6.071e-3*t**2
def ksea(t):    return 0.5667 + 1.775e-3*t - 6.504e-6*t**2
def musea(t):   return (0.9716 + 2.268*math.log10(t)
                        - 2.401*math.log10(t)**2
                        + 0.551*math.log10(t)**3) * 1e-3
def Prsea(t):   return (13.09 - 0.4026*t + 6.317e-3*t**2
                        - 4.784e-5*t**3 + 1.386e-7*t**4)


# ─── Gases (low pressure, Rogers & Mayhew / HEDH) ────────────────────────────
# All functions: rho(p_bara, t_C), others: f(t_C)

def rho_air(p, t):   return p*1e5/(8314.4/28.96*(273.15+t))
def Cp_air(t):       return 1003.716+0.035384*t+0.00028394*t**2+0.00000049078*t**3-0.0000000010188*t**4
def K_air(t):        return 0.024131+0.000079649*t-0.000000038441*t**2+0.000000000015891*t**3
def mu_air(t):       return 0.000017161+0.000000049069*t-0.000000000042916*t**2+5.1084e-14*t**3-3.5316e-17*t**4
def Pr_air(t):       return 0.7137-0.00026517*t+0.0000005083*t**2+0.00000000026031*t**3-8.8693e-13*t**4

def rho_ar(p, t):    return p*1e5/(8314.4/39.948*(273.15+t))
def Cp_ar(t):        return 521.0
def K_ar(t):         return 0.01641+5.153e-5*t-2.818e-8*t**2+1.095e-11*t**3
def mu_ar(t):        return (21.13+0.06284*t-2.855e-5*t**2+9.442e-9*t**3)*1e-6
def Pr_ar(t):        return Cp_ar(t)*mu_ar(t)/K_ar(t)

def rho_co2(p, t):   return p*1e5/(8314.4/44.01*(273.15+t))
def Cp_co2(t):       return 819.9+1.001*t-7.455e-4*t**2+2.15e-7*t**3
def K_co2(t):        return (14.56+0.08244*t+7.559e-7*t**2-9.113e-9*t**3)*1e-3
def mu_co2(t):       return (13.68+0.05047*t-2.213e-5*t**2+6.235e-9*t**3)*1e-6
def Pr_co2(t):       return Cp_co2(t)*mu_co2(t)/K_co2(t)

def rho_co(p, t):    return p*1e5/(8314.4/28.01*(273.15+t))
def Cp_co(t):        return 1037+0.0761*t+3.077e-4*t**2-1.868e-7*t**3
def K_co(t):         return (22.94+0.07273*t-8.923e-6*t**2)*1e-3
def mu_co(t):        return (16.79+0.04506*t-1.792e-5*t**2+4.321e-9*t**3)*1e-6
def Pr_co(t):        return Cp_co(t)*mu_co(t)/K_co(t)

def rho_he(p, t):    return p*1e5/(8314.4/4.003*(273.15+t))
def Cp_he(t):        return 5200.0
def K_he(t):         return (144.3+0.3812*t-0.0001696*t**2+6.975e-8*t**3)*1e-3
def mu_he(t):        return (18.54+0.04708*t-1.728e-5*t**2+6.095e-9*t**3)*1e-6
def Pr_he(t):        return Cp_he(t)*mu_he(t)/K_he(t)

def rho_h2(p, t):    return p*1e5/(8314.4/2.02*(273.15+t))
def Cp_h2(t):        return 14210+2.57*t-0.007258*t**2+9.736e-6*t**3-3.728e-9*t**4
def K_h2(t):         return 0.1673+0.000514*t-3.06e-7*t**2+1.768e-10*t**3
def mu_h2(t):        return (8.5+0.01805*t-2.423e-6*t**2)*1e-6
def Pr_h2(t):        return Cp_h2(t)*mu_h2(t)/K_h2(t)

def rho_ch4(p, t):   return p*1e5/(8314.4/16.043*(273.15+t))
def Cp_ch4(t):       return 2135+3.492*t+1.287e-7*t**2-6.671e-10*t**3
def K_ch4(t):        return (31.01+0.1463*t+9.642e-5*t**2-4.974e-8*t**3)*1e-3
def mu_ch4(t):       return (10.26+0.03108*t-1.319e-5*t**2+3.976e-9*t**3)*1e-6
def Pr_ch4(t):       return Cp_ch4(t)*mu_ch4(t)/K_ch4(t)

def rho_n2(p, t):    return p*1e5/(8314.4/28.013*(273.15+t))
def Cp_n2(t):        return 1038+0.01388*t+3.736e-4*t**2-2.073e-7*t**3
def K_n2(t):         return (24.12+0.0688*t-6.378e-6*t**2)*1e-3
def mu_n2(t):        return (17.02+0.04023*t-8.685e-6*t**2)*1e-6
def Pr_n2(t):        return Cp_n2(t)*mu_n2(t)/K_n2(t)

def rho_o2(p, t):    return p*1e5/(8314.4/31.999*(273.15+t))
def Cp_o2(t):        return 910.7+0.2865*t-1.119e-5*t**2-5.787e-8*t**3
def K_o2(t):         return (24.5+0.08377*t-1.341e-5*t**2)*1e-3
def mu_o2(t):        return (19.75+0.04735*t-9.637e-6*t**2)*1e-6
def Pr_o2(t):        return Cp_o2(t)*mu_o2(t)/K_o2(t)


# ─── Dispatch by fluid code ───────────────────────────────────────────────────

def _fi(Ft: str) -> int:
    return int(Ft[-2:])

def rho(Ft: str, fpar: float, t: float) -> float:
    """Density, kg/m³.  VBA: rho(Ft, fpar, t)"""
    i = _fi(Ft)
    _g = [None,rho_air,rho_ar,rho_co2,rho_co,rho_he,rho_h2,rho_ch4,rho_n2,rho_o2]
    if 1 <= i <= 9: return _g[i](fpar, t)
    if i == 10: return rho_water(t)
    if i == 11: return rho_weg(fpar, t)
    if i == 12: return rho_wpg(fpar, t)
    if i == 13: return rhosea(t)
    raise ValueError(f'Unknown fluid code: {Ft}')

def Cp(Ft: str, fpar: float, t: float) -> float:
    """Specific heat, J/(kg·K).  VBA: Cp(Ft, fpar, t)"""
    i = _fi(Ft)
    _g = [None,Cp_air,Cp_ar,Cp_co2,Cp_co,Cp_he,Cp_h2,Cp_ch4,Cp_n2,Cp_o2]
    if 1 <= i <= 9: return _g[i](t)
    if i == 10: return Cp_water(t)
    if i == 11: return Cp_weg(fpar, t)
    if i == 12: return Cp_wpg(fpar, t)
    if i == 13: return Cpsea(t)
    raise ValueError(f'Unknown fluid code: {Ft}')

def K(Ft: str, fpar: float, t: float) -> float:
    """Thermal conductivity, W/(m·K).  VBA: K(Ft, fpar, t)"""
    i = _fi(Ft)
    _g = [None,K_air,K_ar,K_co2,K_co,K_he,K_h2,K_ch4,K_n2,K_o2]
    if 1 <= i <= 9: return _g[i](t)
    if i == 10: return K_water(t)
    if i == 11: return k_weg(fpar, t)
    if i == 12: return k_wpg(fpar, t)
    if i == 13: return ksea(t)
    raise ValueError(f'Unknown fluid code: {Ft}')

def mu(Ft: str, fpar: float, t: float) -> float:
    """Dynamic viscosity, Pa·s.  VBA: mu(Ft, fpar, t)"""
    i = _fi(Ft)
    _g = [None,mu_air,mu_ar,mu_co2,mu_co,mu_he,mu_h2,mu_ch4,mu_n2,mu_o2]
    if 1 <= i <= 9: return _g[i](t)
    if i == 10: return mu_water(t)
    if i == 11: return mu_weg(fpar, t)
    if i == 12: return mu_wpg(fpar, t)
    if i == 13: return musea(t)
    raise ValueError(f'Unknown fluid code: {Ft}')

def Pr(Ft: str, fpar: float, t: float) -> float:
    """Prandtl number.  VBA: Pr(Ft, fpar, t)"""
    i = _fi(Ft)
    _g = [None,Pr_air,Pr_ar,Pr_co2,Pr_co,Pr_he,Pr_h2,Pr_ch4,Pr_n2,Pr_o2]
    if 1 <= i <= 9: return _g[i](t)
    if i == 10: return Pr_water(t)
    if i == 11: return Pr_weg(fpar, t)
    if i == 12: return Pr_wpg(fpar, t)
    if i == 13: return Prsea(t)
    raise ValueError(f'Unknown fluid code: {Ft}')
