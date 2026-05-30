"""
wcac.surface — Heat transfer and friction correlations.

Faithful translation of Module2.bas from W1279 DMI WCAC Design program I0-1.xlsm.
Includes tube-side Wcool correlations, Bell-Taborek shell-side j/f factors,
and Kays-London entry/exit loss coefficients.
"""
import math
from .fluids import K, mu, Pr, Cp


# ─── Tube side: plain tube (Thermatec functions) ──────────────────────────────

def fcp_plaintube(Re: float, L: float, D: float, kappa: float) -> float:
    """Plain-tube Fanning friction factor, constant fluid properties.
    VBA: fcp_plaintube(Re, L, D, kappa)
    """
    fRe, Kc, C = 16.0, 1.25, 0.00021
    xcross = L / (D * Re) if Re > 0 else 1e9
    flam = (1/Re) * (3.44/xcross**0.5
                     + (Kc/(4*xcross) + fRe - 3.44*xcross**(-0.5))
                     / (1 + C*xcross**(-2)))
    if Re > 100:
        fA = -2*math.log10(kappa/(3.7*D) + 12/Re)
        fB = -2*math.log10(kappa/(3.7*D) + 2.51*fA/Re)
        fC = -2*math.log10(kappa/(3.7*D) + 2.51*fB/Re)
        fturb = (0.065*D/(4*L) + 0.25*(fA-(fB-fA)**2/(fC-2*fB+fA))**(-2))
    else:
        fturb = 0.0
    if L/(2500*D) > 0.01:
        blend = max(0.0, 1 - ((xcross-0.01)/(L/(D*2500)-0.01))**3)
    else:
        blend = 0.0
    fdelta = max(0.0, fturb - flam)
    ftrans = flam + fdelta * blend**6
    if xcross > 0.01:
        return ftrans
    return fturb if fturb > flam else flam


def Nu_plaintube(Re: float, f: float, Pr_: float,
                 L: float, D: float, fpcorr: float) -> float:
    """Plain-tube Nusselt number.  VBA: Nu_plaintube(Re, f, Pr, L, D, fpcorr)"""
    Nufd = 3.66
    Nulowturb = math.exp(-3.796 + 0.795*math.log(Re) + 0.495*math.log(Pr_)
                         - 0.0225*math.log(Pr_)**2)
    Nuhighturb = (f/2*(Re-1000)*Pr_) / (1 + 12.7*(f/2)**0.5*(Pr_**(2/3)-1))
    Nuturb = max(Nulowturb, Nuhighturb)
    Re_lam = min(Re, 2300.0)
    Nulam = Nufd + 0.0677*(Re_lam*Pr_*D/L)**1.33 / (1 + 0.1*Pr_*(Re_lam*D/L)**0.3)
    Nutrans = Nulam * math.exp((Re-2200)/730)
    Nuturbcorr = Nuturb * fpcorr
    return (Nulam**10 + (Nutrans**(-2) + Nuturbcorr**(-2))**(-5))**0.1


# ─── Tube side: heat transfer coefficient ────────────────────────────────────

def h_tube(Re: float, Dto: float, Dti: float, L: float,
           tm: float, tw: float, Ft: str, fpar: float,
           kappa: float, tubetyp: str, config: int,
           condition: str) -> float:
    """Tube-side HTC referred to OD, W/(m²·K).

    condition: 'dry' or 'wet'
    config: +1 shell→tubes (heating), -1 tubes→shell (cooling)
    VBA: h_tube(Re, Dto, Dti, L, tm, tw, Ft, fpar, kappa, tubetyp, config, condition)

    Grooved tube uses Wcool 2.03 tabulated data (6800 < Re < 157700).
    Dry Nu  = max(0.007905·Re^0.9537, 0.04427·Re^0.8  )^(1/80)·Pr^0.3
    Wet Nu  = max(0.01198· Re^0.9384, 0.07627·Re^0.7723)^(1/80)·Pr^0.3
    """
    if Ft[0] == 'g':
        nfp = 0.47 if config == 1 else 0.0
        fpcorr = ((273.15+tm) / (273.15+tw)) ** nfp
    else:
        nfp = 0.11 if config == 1 else 0.25
        fpcorr = (mu(Ft, fpar, tm) / mu(Ft, fpar, tw)) ** nfp

    if tubetyp[0].upper() == 'P':
        f = fcp_plaintube(Re, L, Dti, kappa)
        h = K(Ft, fpar, tm) / Dto * Nu_plaintube(Re, f, Pr(Ft,fpar,tm), L, Dti, fpcorr)
        if condition == 'wet':
            h *= 10**(0.1102 - 1.367e-7 * Re)
    else:
        # Grooved tube — Wcool ACTUBE curve fits
        if condition == 'dry':
            Nu = ((0.007905*Re**0.9537)**80 + (0.04427*Re**0.8)**80)**(1/80)
        else:
            Nu = ((0.01198*Re**0.9384)**80 + (0.07627*Re**0.7723)**80)**(1/80)
        Nu *= Pr(Ft, fpar, tm)**0.3
        h = K(Ft, fpar, tm) / Dto * Nu
    return h


# ─── Tube side: friction factor ───────────────────────────────────────────────

def f_tube(Re: float, L: float, Dti: float, kappa: float,
           Ft: str, fpar: float, tm: float, tw: float,
           tubetyp: str, config: int):
    """Tube-side Fanning friction factor with variable-property correction.

    Returns (f, cfp_corr).
    Grooved tube: f = 0.2478 · Re^(-0.135)  (Wcool 2.03, no correction)
    Plain tube:   f = fcp_plaintube × correction
    VBA: f_tube(Re, L, Dti, kappa, Ft, fpar, tm, tw, tubetyp, config)
    """
    if tubetyp[0].upper() == 'P':
        if Ft[0] == 'g':
            if Re >= 4000:   m = -0.1
            elif config == -1: m = 0.81
            else:            m = 0.0
            cfp_corr = ((273.15+tw) / (273.15+tm)) ** m
        else:
            if Re >= 4000:   m = 0.24 if config == -1 else 0.25
            else:            m = 0.54 if config == -1 else 0.58
            cfp_corr = (mu(Ft, fpar, tw) / mu(Ft, fpar, tm)) ** m
        f = fcp_plaintube(Re, L, Dti, kappa) * cfp_corr
    else:
        cfp_corr = 1.0
        f = 0.2478 * Re**(-0.135)
    return f, cfp_corr


# ─── Shell side: Bell-Taborek j and f factors ─────────────────────────────────

def f_shell(Re: float, D: float, Xt: float, pattern: str) -> float:
    """Shell-side Fanning friction factor for tube bundles.
    Bell-Taborek tabulated coefficients.
    VBA: f_shell(Re, D, Xt, pattern)  — pattern: 'T', 'S', or 'RS'
    """
    if not (0.005 <= D < 0.055):
        return 0.0
    if pattern == 'RS':
        if Re < 10:      b1, b2 = 32.0,  -1.0
        elif Re < 100:   b1, b2 = 26.2,  -0.913
        elif Re < 1000:  b1, b2 = 3.5,   -0.476
        elif Re < 10000: b1, b2 = 0.333, -0.136
        else:            b1, b2 = 0.303, -0.126
        return b1 * (1.33*D/(0.7071*Xt))**(6.59/(1+0.14*Re**0.52)) * Re**b2
    elif pattern == 'S':
        if Re < 10:      b1, b2 = 35.0,   -1.0
        elif Re < 100:   b1, b2 = 32.1,   -0.963
        elif Re < 1000:  b1, b2 = 6.09,   -0.602
        elif Re < 10000: b1, b2 = 0.0815,  0.022
        else:            b1, b2 = 0.391,  -0.148
        return b1 * (1.33*D/Xt)**(6.3/(1+0.14*Re**0.378)) * Re**b2
    else:  # T
        if Re < 10:      b1, b2 = 48.0,   -1.0
        elif Re < 100:   b1, b2 = 45.1,   -0.973
        elif Re < 1000:  b1, b2 = 4.57,   -0.476
        elif Re < 10000: b1, b2 = 0.486,  -0.152
        else:            b1, b2 = 0.372,  -0.123
        return b1 * (1.33*D/Xt)**(7/(1+0.14*Re**0.5)) * Re**b2


def j_shell(Re: float, D: float, Xt: float, pattern: str) -> float:
    """Shell-side Colburn j-factor for tube bundles.
    Bell-Taborek tabulated coefficients.
    VBA: j_shell(Re, D, Xt, pattern)
    """
    if not (0.005 <= D < 0.055):
        return 0.0
    if pattern == 'RS':
        if Re < 10:    a1, a2 = 1.55,  -0.667
        elif Re < 100: a1, a2 = 1.498, -0.656
        elif Re < 1000:a1, a2 = 0.73,  -0.5
        else:          a1, a2 = 0.37,  -0.396
        return a1 * (1.33*D/(0.7071*Xt))**(1.93/(1+0.14*Re**0.5)) * Re**a2
    elif pattern == 'S':
        if Re < 10:      a1, a2 = 0.97,  -0.667
        elif Re < 100:   a1, a2 = 0.9,   -0.631
        elif Re < 1000:  a1, a2 = 0.408, -0.46
        elif Re < 10000: a1, a2 = 0.107, -0.266
        else:            a1, a2 = 0.37,  -0.395
        return a1 * (1.33*D/Xt)**(1.187/(1+0.14*Re**0.37)) * Re**a2
    else:  # T
        if Re < 10:    a1, a2 = 1.4,  -0.667
        elif Re < 100: a1, a2 = 1.36, -0.657
        elif Re < 1000:a1, a2 = 0.593,-0.477
        else:          a1, a2 = 0.321,-0.388
        return a1 * (1.33*D/Xt)**(1.45/(1+0.14*Re**0.519)) * Re**a2


# ─── Entry/exit loss coefficients (Kays-London) ───────────────────────────────

def KcKe(Re: float, D: float, L: float, sigma: float):
    """Kc and Ke by interpolation of Kays-London Figure 5-2 (multiple round channels).
    Valid 0.2 ≤ sigma ≤ 0.54.
    VBA: KcKe(Re, D, L, sigma) → (Kc, Ke)
    """
    xplus_opt = [20, 0.2, 0.1, 0.05]
    Re_opt    = [3000, 5000, 10000, 1000000]
    sigma_opt = [0.2, 0.37, 0.54]
    kc_opt = [0.994,0.983,0.926,0.8, 0.456,0.443,0.426,0.329,
              0.925,0.912,0.858,0.734, 0.385,0.371,0.356,0.259,
              0.857,0.843,0.792,0.666, 0.32,0.305,0.288,0.193]
    ke_opt = [0.517,0.517,0.517,0.554, 0.614,0.614,0.629,0.643,
              0.158,0.158,0.183,0.232, 0.357,0.357,0.37,0.406,
             -0.143,-0.134,-0.105,-0.039, 0.151,0.159,0.167,0.209]

    xp = 4*L/(D*Re) if Re > 0 else 1e9
    si = 1
    while si > 0 and sigma < sigma_opt[si]:  si -= 1
    ri = 2
    while ri > 0 and Re < Re_opt[ri]:         ri -= 1
    xi = 2
    while xi > 0 and xp >= xplus_opt[xi]:     xi -= 1

    def lerp(a, b, x, x0, x1):
        return (a-b)/(x0-x1)*(x-x1)+b

    if Re < 3000:
        i1 = xi + 8*si;  i2 = xi + 8*(si+1)
        if 0.05 <= xp <= 20:
            kc1=lerp(kc_opt[i1],kc_opt[i1+1],xp,xplus_opt[xi],xplus_opt[xi+1])
            kc2=lerp(kc_opt[i2],kc_opt[i2+1],xp,xplus_opt[xi],xplus_opt[xi+1])
            ke1=lerp(ke_opt[i1],ke_opt[i1+1],xp,xplus_opt[xi],xplus_opt[xi+1])
            ke2=lerp(ke_opt[i2],ke_opt[i2+1],xp,xplus_opt[xi],xplus_opt[xi+1])
        elif xp > 20:
            kc1,kc2,ke1,ke2=kc_opt[i1],kc_opt[i2],ke_opt[i1],ke_opt[i2]
        else:
            kc1,kc2,ke1,ke2=kc_opt[i1+1],kc_opt[i2+1],ke_opt[i1+1],ke_opt[i2+1]
    else:
        i1 = 4+ri+8*si;  i2 = 4+ri+8*(si+1)
        if Re <= 1000000:
            kc1=lerp(kc_opt[i1],kc_opt[i1+1],Re,Re_opt[ri+1],Re_opt[ri])
            kc2=lerp(kc_opt[i2],kc_opt[i2+1],Re,Re_opt[ri+1],Re_opt[ri])
            ke1=lerp(ke_opt[i1],ke_opt[i1+1],Re,Re_opt[ri+1],Re_opt[ri])
            ke2=lerp(ke_opt[i2],ke_opt[i2+1],Re,Re_opt[ri+1],Re_opt[ri])
        else:
            kc1,kc2,ke1,ke2=kc_opt[i1+1],kc_opt[i2+1],ke_opt[i1+1],ke_opt[i2+1]

    if 0.2 <= sigma <= 0.54:
        Kc = lerp(kc1, kc2, sigma, sigma_opt[si], sigma_opt[si+1])
        Ke = lerp(ke1, ke2, sigma, sigma_opt[si], sigma_opt[si+1])
    elif sigma > 0.54:
        Kc, Ke = kc2, ke2
    else:
        Kc, Ke = kc1, ke1
    return Kc, Ke
