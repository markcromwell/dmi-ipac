"""
wcac.units — Unit conversion functions.

Faithful translation of Module4.bas from W1279 DMI WCAC Design program I0-1.xlsm.
All conversions preserve the exact factors used in the VBA.
"""
from .fluids import rho, Mw


# ─── Temperature ──────────────────────────────────────────────────────────────

def F_to_C(f: float) -> float:  return (f - 32.0) / 1.8
def C_to_F(c: float) -> float:  return c * 1.8 + 32.0

def UoMi_temp(uom: str, value: float) -> float:
    """Input temperature to °C.  VBA: UoMi_temp(uom, value)"""
    if uom in ('°C', 'C'): return value
    if uom in ('°F', 'F'): return (value - 32) / 1.8
    raise ValueError(f'Unknown temperature UoM: {uom}')

def UoMo_temp(uom: str, value_C: float) -> float:
    """°C to output temperature.  VBA: UoMo_temp(uom, value)"""
    if uom in ('°C', 'C'): return value_C
    if uom in ('°F', 'F'): return value_C * 1.8 + 32
    raise ValueError(f'Unknown temperature UoM: {uom}')


# ─── Pressure ─────────────────────────────────────────────────────────────────

def UoMi_press(uom: str, value: float) -> float:
    """Input pressure to bar(a).  VBA: UoMi_press(uom, value)
    Note: VBA uses 14.5 psi/bar (not 14.696) — preserved exactly.
    """
    if uom in ('bar(a)', 'bara', 'barg'): return value
    if uom in ('mbar(a)', 'mbarg'):       return value / 1000
    if uom in ('kPa(a)', 'kPag'):         return value / 100
    if uom in ('psi(a)', 'psia', 'psig'): return value / 14.5
    raise ValueError(f'Unknown pressure UoM: {uom}')

def UoMo_press(uom: str, value_bara: float) -> float:
    """bara to output pressure.  VBA: UoMo_press(uom, value)"""
    if uom == 'bar(a)':     return value_bara
    if uom == 'mbar(a)':    return value_bara * 1000
    if uom == 'kPa(a)':     return value_bara * 100
    if uom == 'psi(a)':     return value_bara * 14.5
    raise ValueError(f'Unknown pressure UoM: {uom}')

def psig_to_bara(psig: float) -> float:
    """psig → bara using exact spreadsheet factor (14.5 psi/bar)."""
    return (psig + 14.696) / 14.5

def psia_to_bara(psia: float) -> float:
    return psia / 14.5

def kPa_to_psi(kPa: float) -> float:
    """kPa → psi using standard factor (not the VBA 14.5)."""
    return kPa * 0.14504


# ─── Flow rate ────────────────────────────────────────────────────────────────

_SCFM_DENSITY_BARA  = 1.0138    # bara (≈14.7 psia = 14.5 × 1.0138)
_SCFM_DENSITY_TC    = 15.5556   # °C (= 60°F) — US industry std
_FT3_PER_M3         = 3.281**3  # 35.315 ft³/m³


def UoMi_flow(uom: str, value: float, Ftype: str,
              fpar: float, t: float, omega: float) -> tuple:
    """Input flow rate to kg/s.  Returns (mdot_kgs, type_flag).
    type_flag: 'm' = mass-based, 'v' = volume-based.
    VBA: UoMi_flow(uom, value, Ftype, fpar, t, omega)

    Scfm reference: US industry standard 0.075 lb/ft³ air = 60°F / 14.5 psia.
    """
    u = uom.strip()
    rho_fluid = rho(Ftype, fpar, t)

    if u == 'kg/s':    return value, 'm'
    if u == 'kg/min':  return value / 60, 'm'
    if u == 'kg/h':    return value / 3600, 'm'
    if u == 'lb/s':    return value / 2.205, 'm'
    if u == 'lb/min':  return value / (2.205 * 60), 'm'
    if u == 'lb/h':    return value / (2.205 * 3600), 'm'

    if u == 'litre/min': return value * rho_fluid / 60000, 'v'
    if u == 'm3/s':    return value * rho_fluid, 'v'
    if u == 'm3/h':    return value * rho_fluid / 3600, 'v'
    if u == 'USgpm':   return value * 0.8327 * rho_fluid / (220 * 60), 'v'

    if u == 'Acfm':
        # Actual volume at fpar / t, corrected for moisture
        mdot = (value * rho_fluid / (_FT3_PER_M3 * 60)
                * (1 + omega) / (1 + Mw(Ftype)*omega/18.015))
        return mdot, 'v'
    if u in ('Am3/s', 'Am³/s'):
        return (value * rho_fluid * (1+omega) / (1+Mw(Ftype)*omega/18.015)), 'v'
    if u in ('Am3/h', 'Am³/h'):
        return (value * rho_fluid / 3600 * (1+omega) / (1+Mw(Ftype)*omega/18.015)), 'v'

    if u == 'Nm3/h':
        rho_n = rho(Ftype, 1.01325, 0)
        return value * rho_n / 3600, 'm'
    if u == 'Scfm':
        # US std: 0.075 lb/ft³ air ≡ 60°F / 14.5 psia
        rho_std = rho(Ftype, _SCFM_DENSITY_BARA, _SCFM_DENSITY_TC)
        return value * rho_std / (_FT3_PER_M3 * 60), 'm'

    raise ValueError(f'Unknown flow UoM: {uom!r}')


def UoMo_flow(uom: str, mdot_kgs: float, Ftype: str,
              fpar: float, t: float, omega: float) -> float:
    """kg/s to output flow rate.  VBA: UoMo_flow(uom, value, Ftype, fpar, t, omega)"""
    u = uom.strip()
    rho_fluid = rho(Ftype, fpar, t)

    if u == 'kg/s':    return mdot_kgs
    if u == 'kg/min':  return mdot_kgs * 60
    if u == 'kg/h':    return mdot_kgs * 3600
    if u == 'lb/s':    return mdot_kgs * 2.205
    if u == 'lb/min':  return mdot_kgs * 2.205 * 60
    if u == 'lb/h':    return mdot_kgs * 2.205 * 3600

    if u == 'litre/min': return mdot_kgs / rho_fluid * 1000 * 60
    if u == 'm3/s':    return mdot_kgs / rho_fluid
    if u == 'm3/h':    return mdot_kgs / rho_fluid * 3600
    if u == 'USgpm':   return mdot_kgs / (rho_fluid * 0.8327) * 220 * 60

    if u == 'Acfm':
        vol_m3s = mdot_kgs / (rho_fluid * (1+omega) / (1+Mw(Ftype)*omega/18.015))
        return vol_m3s * _FT3_PER_M3 * 60
    if u in ('Am3/s', 'Am³/s'):
        return mdot_kgs / (rho_fluid * (1+omega) / (1+Mw(Ftype)*omega/18.015))
    if u in ('Am3/h', 'Am³/h'):
        return (mdot_kgs / (rho_fluid * (1+omega) / (1+Mw(Ftype)*omega/18.015))) * 3600

    if u == 'Nm3/h':
        return mdot_kgs / rho(Ftype, 1.01325, 0) * 3600
    if u == 'Scfm':
        rho_std = rho(Ftype, _SCFM_DENSITY_BARA, _SCFM_DENSITY_TC)
        return mdot_kgs / rho_std * _FT3_PER_M3 * 60

    raise ValueError(f'Unknown flow UoM: {uom!r}')


# ─── HTC and fouling ──────────────────────────────────────────────────────────

def Wm2K_to_Btu(h: float) -> float:
    """W/(m²·K) → Btu/(h·ft²·R)"""
    return h * 0.17611

def Btu_to_Wm2K(h: float) -> float:
    """Btu/(h·ft²·R) → W/(m²·K)"""
    return h * 5.6783

def fouling_imp_to_SI(R_imp: float) -> float:
    """R·ft²·h/Btu → K·m²/W"""
    return R_imp * 0.17611
