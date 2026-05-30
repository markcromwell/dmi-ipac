"""
wcac.solver — Thermal performance calculations.

Faithful translation of Module3.bas from W1279 DMI WCAC Design program I0-1.xlsm.

Key functions (VBA names preserved):
  dew_point      — gas dew point via Pswater bisection
  outlet_temp    — outlet temperature given Q (enthalpy-based for gas)
  wetwall_temp   — tube wall temperature in condensing zone (McQuiston)
  h_shell        — shell-side HTC with Bell-Delaware corrections
  Jtotal         — total Bell-Delaware correction factor
  tubewall       — iterate to converged wall temperatures and U
  dPsolver       — tube-side pressure drop with density iteration
  QsolverSP      — single-phase NTU-effectiveness solver
  Qsolver        — two-zone wet/dry solver (enthalpy-based LMED)
"""
import math
from .fluids import (rho, Cp, K, mu, Pr, Mw,
                     Pswater, hgwater, hfwater, Cpgwater)
from .surface import h_tube, f_tube, j_shell, KcKe


# ─── Humidity / dew point ─────────────────────────────────────────────────────

def dew_point(Ft: str, fpar: float, omega: float) -> float:
    """Gas dew point, °C.  fpar in bara.
    VBA: dew_point(Ft, fpar, omega)
    """
    if omega <= 0:
        return -273.15
    Ps = omega * fpar * 1e5 / (18.015/Mw(Ft) + omega)
    td = 373.0; tdelta = 186.795
    for _ in range(1000):
        Psw = Pswater(td)
        if abs(Psw - Ps) <= 1:
            break
        td = td - tdelta if Psw > Ps else td + tdelta
        tdelta /= 2
    if td < 0.01 or td > 373:
        return -273.15
    return td


# ─── Outlet temperature ───────────────────────────────────────────────────────

def outlet_temp(Ft: str, fpar: float, Q: float, mdot: float,
                ti: float, tomax: float, dp: float,
                omegai: float, config: int) -> float:
    """Outlet temperature (°C) given Q in kW.
    config: +1 = shell side heated, -1 = tube side cooled.
    VBA: outlet_temp(Ft, fpar, Q, mdot, ti, tomax, dp, omegai, config)

    For gases, uses enthalpy definition consistent with Wcool (RJG email 19 Jun 2024).
    """
    t = tomax; tlast = ti; count = 0
    if Ft[0] == 'l':
        while abs(t - tlast) > 0.0001 and count < 100:
            count += 1; tlast = t
            t = ti - Q * 1000 * config / (mdot * Cp(Ft, fpar, (ti+t)/2))
    else:
        tdelta = ti - t
        while abs(t - tlast) > 0.0001 and count < 100:
            count += 1; tlast = t; tdelta /= 2
            t = max(t, 0.01)
            Psw = Pswater(t)
            if t <= 0.01:
                omegao = 0.0
            else:
                denom = fpar*1e5 - dp*1000 - Psw
                omegao = 18.015/Mw(Ft)*Psw/denom if denom > 0 else omegai
                if omegai < omegao or omegao < 0:
                    omegao = omegai
            Qguess = (mdot/(1+omegai)
                      * (Cp(Ft,fpar,ti)*ti + omegai*hgwater(ti)
                         - Cp(Ft,fpar,t)*t - omegao*hgwater(t))
                      * config / 1000)
            t = t + tdelta if Qguess > Q else t - tdelta
            t = max(t, 0.01)
    return t


# ─── Wet wall temperature ─────────────────────────────────────────────────────

def wetwall_temp(Ft: str, fpar: float, omega: float,
                 Rt: float, hs: float, ht: float,
                 ts: float, tt: float):
    """Tube wall temperature in condensing zone.  McQuiston method.
    Returns (tw, count, tsw).
    VBA: wetwall_temp(Ft, fpar, omega, Rt, hs, ht, ts, tt)
    """
    tw = 0.5*(tt + ts); tdelta = (tt - ts)/4
    Eb = (Cp(Ft,fpar,tt)*tt + omega*hgwater(tt)) / (1+omega)
    count = 0
    for _ in range(100):
        Psw = Pswater(tw)
        denom = fpar*1e5 - Psw
        omegaw = 18.015/Mw(Ft)*Psw/denom if denom > 0 else 0.0
        Ew = Cp(Ft,fpar,tw)*tw + omegaw*hgwater(tw)   # VBA line 1185 (not divided by 1+omegaw)
        lhs = (Rt + hs**(-1))**(-1) * (tw - ts)
        rhs = ht/Cp(Ft,fpar,tt) * (Eb - Ew/(1+omegaw))
        if abs(lhs/rhs - 1) <= 0.001:
            break
        tw = tw - tdelta if lhs > rhs else tw + tdelta
        tdelta /= 2; count += 1
    Psw = Pswater(tw)
    denom2 = fpar*1e5 - Psw
    omegaw = 18.015/Mw(Ft)*Psw/denom2 if denom2 > 0 else 0.0
    Ew = (Cp(Ft,fpar,tw)*tw + omegaw*hgwater(tw)) / (1+omegaw)
    tsw = (ht/Cp(Ft,fpar,tt) * (Eb - Ew)) / hs + ts
    return tw, count, tsw


# ─── Shell-side HTC ───────────────────────────────────────────────────────────

def h_shell(Re: float, tb: float, tw: float, D: float, Xt: float,
            jtot: float, Ft: str, fpar: float,
            config: int, pattern: str) -> float:
    """Shell-side HTC, W/(m²·K).
    VBA: h_shell(Re, tb, tw, D, Xt, jtot, Ft, fpar, config, pattern)
    """
    if Ft[0] == 'g':
        nfp = 0.25 if config == -1 else 0.0
        fpcorr = ((273.15+tb) / (273.15+tw)) ** nfp
    else:
        fpcorr = (mu(Ft, fpar, tb) / mu(Ft, fpar, tw)) ** 0.14
    return (j_shell(Re, D, Xt, pattern) * Re
            * Pr(Ft, fpar, tb)**(1/3) * (K(Ft, fpar, tb)/D)
            * jtot * fpcorr)


# ─── Bell-Delaware correction factors ────────────────────────────────────────

def Jtotal(Re: float, Jc: float, Jl: float,
           Abas: float, Acs: float, Nss: int,
           Ntcc: float, Ntcw: float,
           Nb: int, Lbe: float, Lbc: float) -> float:
    """Total Bell-Delaware correction factor Jtot = Jc·Jl·Jb·Jr·Js.
    Jc and Jl are pre-computed (from geometry sheet cells) and passed in.
    Jb, Jr, Js are computed internally.
    VBA: Jtotal(Re, Jc, Jl, Abas, Acs, Nss, Ntcc, Ntcw, Nb, Lbe, Lbc)

    Js formula: geometry sheet F40 display formula Nb/((Nb-1)+x) is used
    (x = Lbe/Lbc) rather than the VBA-internal formula with 2·x^0.4 terms.
    See CALCULATION_DISCREPANCIES.md for discussion.
    Both are computed and available via Jtotal_both().
    """
    if Re >= 100:
        cbh = 1.25; Jr = 1.0
    else:
        cbh = 1.35
        Jrmax = (10 / ((Ntcc + Ntcw) * (Nb + 1)))**0.18
        Jr = Jrmax if Re <= 20 else Jrmax + (20-Re)/80*(Jrmax-1)

    Jb1 = math.exp(-cbh * Abas/Acs * (1 - (2*Nss/Ntcc)**(1/3))) if Ntcc > 0 else 1.0
    Jb = min(Jb1, 1.0)

    x = Lbe / Lbc
    # Display formula (geometry sheet F40) — used as default
    Js = Nb / ((Nb-1) + x)
    # VBA alternative: Js_VBA = ((Nb-1) + 2*x**(1-N)) / ((Nb-1) + 2*x)  where N=0.6

    return Jc * Jl * Jb * Jr * Js


def Jtotal_both(Re: float, Jc: float, Jl: float,
                Abas: float, Acs: float, Nss: int,
                Ntcc: float, Ntcw: float,
                Nb: int, Lbe: float, Lbc: float) -> dict:
    """Return both display and VBA variants of all J factors.
    Useful for displaying both values to the engineer (see CALCULATION_DISCREPANCIES.md).
    """
    N = 0.6 if Re >= 100 else 1/3
    if Re >= 100:
        cbh = 1.25; Jr = 1.0
    else:
        cbh = 1.35
        Jrmax = (10 / ((Ntcc + Ntcw) * (Nb + 1)))**0.18
        Jr = Jrmax if Re <= 20 else Jrmax + (20-Re)/80*(Jrmax-1)
    Jb1 = math.exp(-cbh * Abas/Acs * (1-(2*Nss/Ntcc)**(1/3))) if Ntcc > 0 else 1.0
    Jb = min(Jb1, 1.0)
    x = Lbe / Lbc
    Js_display = Nb / ((Nb-1) + x)
    Js_VBA     = ((Nb-1) + 2*x**(1-N)) / ((Nb-1) + 2*x)
    return {
        'Jc': Jc, 'Jl': Jl, 'Jb': Jb, 'Jr': Jr,
        'Js_display': Js_display, 'Js_VBA': Js_VBA,
        'Jtot_display': Jc*Jl*Jb*Jr*Js_display,
        'Jtot_VBA':     Jc*Jl*Jb*Jr*Js_VBA,
    }


# ─── Tube wall iteration ──────────────────────────────────────────────────────

def tubewall(tms: float, tmt: float, Gt: float, Res: float,
             Dto: float, Dti: float, Xt: float, Lt: float,
             jtot: float, Rt: float,
             Ftt: str, Fts: str, fpart: float, fpars: float,
             Rfs: float, Rft: float, kappa: float,
             tubetyp: str, config: int, condition: str, pattern: str):
    """Iterate to converged tube wall temperatures and U.
    Returns (twi, two, U, count, ht, hs).
    VBA: tubewall(tms, tmt, Gt, Res, Dto, Dti, Xt, Lt, jtot, Rt, ...)
    """
    twi = tmt; two = tms
    Ret = Gt * Dti / max(mu(Ftt, fpart, tmt), 1e-12)
    ht = h_tube(Ret, Dto, Dti, Lt, tmt, twi, Ftt, fpart, kappa, tubetyp, config, condition)
    hs = h_shell(Res, tms, two, Dto, Xt, jtot, Fts, fpars, config, pattern)
    U = (hs**(-1) + Rfs + Rt + Dto*Rft/Dti + ht**(-1))**(-1)
    Ulast = 1.05 * U; count = 0
    for _ in range(100):
        if abs(U/Ulast - 1) <= 0.001: break
        Ulast = U
        twi = tmt + U/(ht**(-1) + Dto*Rft/Dti)**(-1) * (tms - tmt)
        two = tms - U/(hs**(-1) + Rfs)**(-1) * (tms - tmt)
        ht = h_tube(Ret, Dto, Dti, Lt, tmt, twi, Ftt, fpart, kappa, tubetyp, config, condition)
        hs = h_shell(Res, tms, two, Dto, Xt, jtot, Fts, fpars, config, pattern)
        U = (hs**(-1) + Rfs + Rt + Dto*Rft/Dti + ht**(-1))**(-1)
        count += 1
    return twi, two, U, count, ht, hs


# ─── Tube-side pressure drop ──────────────────────────────────────────────────

def dPsolver(t_i: float, t_o: float, tw: float,
             Ft: str, fpar: float, G: float,
             D: float, L: float, sigma: float,
             omegai: float, kappa: float,
             tubetyp: str, config: int) -> tuple:
    """Tube-side pressure drop, kPa.  Iterates for density change.
    Returns (dP, dP_last, count, f, cfp_corr, Kc, Ke, omegao).
    VBA: dPsolver(t_i, t_o, tw, Ft, fpar, G, D, L, sigma, omegai, kappa, tubetyp, config)

    Grooved tube: dP = 0.8 × Gcor² / (2000·ρ_m) × (4·L·f/D)
      where f = 0.2478·Re^(-0.135)  and 0.8 is the I0-1 correction (vba line 1506).
    Plain tube:   full Kays-London entry/exit + Darcy friction.
    """
    tm = 0.5*(t_i + t_o)
    Re = G * D / max(mu(Ft, fpar, tm), 1e-12)
    f, cfp = f_tube(Re, L, D, kappa, Ft, fpar, tm, tw, tubetyp, config)
    rho_i = rho(Ft, fpar, t_i) * (1+omegai) / (1 + (Mw(Ft)/18.015)*omegai)
    rho_o = rho(Ft, fpar, t_o) * (1+omegai) / (1 + (Mw(Ft)/18.015)*omegai)
    rho_m = 0.5*(rho_i + rho_o)
    dP = G**2 / (2000*rho_m) * (4*L*f/D)
    dPlast = dP*1.1; omegao = omegai; Kc = 0.0; Ke = 0.0; count = 0

    for _ in range(100):
        if abs(dP/dPlast - 1) <= 0.001: break
        dPlast = dP; count += 1
        Po = max(fpar - dP/100, 1e-5)
        Psw = Pswater(t_o); denom = Po*1e5 - Psw
        omegao = 18.015/Mw(Ft)*Psw/denom if denom > 0 else omegai
        if omegai < omegao or omegao < 0: omegao = omegai
        rho_o = rho(Ft, Po, t_o) * (1+omegao) / (1+(Mw(Ft)/18.015)*omegao)
        rho_m = 0.5*(rho_i + rho_o)
        Gcor = G * (1 + 0.5*(omegai+omegao)) / (1+omegai)
        Re2 = Gcor * D / max(mu(Ft, fpar, tm), 1e-12)
        f, cfp = f_tube(Re2, L, D, kappa, Ft, fpar, tm, tw, tubetyp, config)
        if tubetyp[0].upper() == 'P':
            Kc, Ke = KcKe(Re2, D, L, sigma)
            dP = (Gcor**2 / (2000*rho_i)
                  * ((1-sigma**2+Kc) + 4*L*f/D*(rho_i/rho_m)
                     + 2*(rho_i/rho_o - 1) - (1-sigma**2-Ke)*rho_i/rho_o))
        else:
            # Grooved tube: 0.8x correction (I0-1 release notes, 2025-05-29)
            dP = 0.8 * Gcor**2 / (2000*rho_m) * (4*L*f/D)

    return dP, dPlast, count, f, cfp, Kc, Ke, omegao


# ─── Single-phase solver ──────────────────────────────────────────────────────

def QsolverSP(tit, tis, config, Ftt, Fts, fpart, fpars,
              mdots, mdott, omegai, Act, Acs, A, SAM,
              Rfs, Rft, Dto, Dti, Lt, Xt, Jc, Jl, Abas,
              Nss, Ntcc, Ntcw, Nb, Lbe, Lbc, kappa, Rt, tubetyp, pattern):
    """NTU-effectiveness solver for single-phase (all-dry) heat transfer.
    Returns array: [Q_kW, Q_last, count, twi, two, U, Ucount, ht, hs, 0, 0].
    VBA: QsolverSP(...)
    """
    Gt = mdott/Act; Gs = mdots/Acs
    tot = tis + tit/2
    Qguess = (mdott/(1+omegai)
              * ((Cp(Ftt,fpart,tit)*tit - Cp(Ftt,fpart,tot)*tot)
                 + omegai*(hgwater(tit) - hgwater(tot))) / 1000)
    Qguesslast = Qguess*1.1; count = 0
    U = 0; twi = tit; two = tis; ht = 0; hs = 0; Ucount = 0

    for _ in range(100):
        if abs(Qguesslast/Qguess - 1) <= 0.001: break
        Qguesslast = Qguess; count += 1
        tot = outlet_temp(Ftt, fpart, Qguess, mdott, tit, tis, 0, omegai, -config)
        tmt = (tit + tot)/2
        Ct  = abs(Qguess*1000 / max(tit-tot, 1e-9))
        tos = outlet_temp(Fts, fpars, Qguess, mdots, tis, tit, 0, 0, config)
        tms = (tis + tos)/2
        Cs  = mdots * Cp(Fts, fpars, tms)
        Res = Gs * Dto / max(mu(Fts, fpars, tms), 1e-12)
        jtot = Jtotal(Res, Jc, Jl, Abas, Acs, Nss, Ntcc, Ntcw, Nb, Lbe, Lbc)
        twi, two, U, Ucount, ht, hs = tubewall(
            tms, tmt, Gt, Res, Dto, Dti, Xt, Lt, jtot, Rt,
            Ftt, Fts, fpart, fpars, Rfs, Rft, kappa, tubetyp, config, 'dry', pattern)
        Cmax = max(Ct, Cs); Cmin = min(Ct, Cs); R = Cmin/Cmax
        NTU  = U * A * (1 - 0.01*SAM) / Cmin
        Eff  = (1 - math.exp(-NTU*(1-R))) / (1 - R*math.exp(-NTU*(1-R)))
        Qguess = Eff * Cmin / 1000 * (tis - tit) * config

    return [Qguess, Qguesslast, count, twi, two, U, Ucount, ht, hs, 0, 0]


# ─── Two-zone wet/dry solver ──────────────────────────────────────────────────

def Qsolver(tit, tis, config, Ftt, Fts, fpart, fpars,
            mdots, mdott, omegai, Act, Acs, A, SAM,
            Rfs, Rft, Dto, Dti, Lt, sigmat, Xt, Jc, Jl, Abas,
            Nss, Ntcc, Ntcw, Nb, Lbe, Lbc, kappa, Rt, tubetyp, pattern):
    """Two-zone (dry + condensing) heat transfer solver.
    Core of the W1279 calculation engine.
    VBA: Qsolver(tit, tis, config, ...)

    Returns array (22 elements):
      [0]  Q_kW         total heat, kW
      [1]  Qcount       outer iterations
      [2]  U            overall HTC, W/(m²·K)
      [3]  Ucount       U inner iterations
      [4]  dpt          tube dP, kPa
      [5]  dptcount     dP iterations
      [6]  t2t          dry/wet zone boundary temperature, °C
      [7]  t2tw         tube wall temp at dry/wet boundary, °C
      [8]  totw         tube wall temp at outlet, °C
      [9]  wetwallcount wet-wall iterations
      [10] tmtw         mean tube wall temp, °C
      [11] tmsw         mean shell wall temp, °C
      [12] Areqdry      dry zone heat transfer area, m²
      [13] ht           average effective tube-side HTC
      [14] hs           average effective shell-side HTC
      [15] htmt         mass-transfer HTC / Cp
      [16] LMED         enthalpy-based mean driving force, J/kg
      [17] tsw_inletdry shell wall temp at tube inlet (dry zone)
      [18] tsw_2dry     shell wall temp at dry/wet zone junction
      [19] tsw_2wet     tube wall temp inside (wet zone junction)
      [20] tsw_outwet   tube wall temp inside at outlet
    """
    dp_dew = dew_point(Ftt, fpart, omegai)

    if dp_dew < tis:
        # All-dry: delegate to single-phase solver
        Qa = QsolverSP(tit,tis,config,Ftt,Fts,fpart,fpars,mdots,mdott,
                       omegai,Act,Acs,A,SAM,Rfs,Rft,Dto,Dti,Lt,Xt,
                       Jc,Jl,Abas,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc,kappa,Rt,tubetyp,pattern)
        Qg,U,ht,hs=Qa[0],Qa[5],Qa[7],Qa[8]
        tos=outlet_temp(Fts,fpars,Qg,mdots,tis,tit,0,0,config)
        tot=outlet_temp(Ftt,fpart,Qg,mdott,tit,tis,0,omegai,-config)
        return [Qg,0,U,Qa[6],0,0,tit,dp_dew,tis,0,Qa[3],Qa[4],A,ht,hs,0,0,0,0,0,0]

    # ── Condensing case ──────────────────────────────────────────────────────
    Gt = mdott/Act; Gs = mdots/Acs
    tot = (tis+tit)/2; totdelta = (tit-tis)/4
    Areq = A*(1-0.01*SAM)+1; count1 = 0
    Qguess=0; tos=tis; tms=tis; jtot=1.0; Gtcor=Gt
    tmtw=tit; tmsw=tis; ht=0; hs=0; htdry=0; hsdry=0
    dpt=0; dptcount=0; Ucount=0; omegao=omegai
    t2t=tit; t2tw=dp_dew; totw=tis; Areqdry=0; Areqwet=0
    htmt=0; LMED=0; QSF=0; tmtwdry=tit; t2s=tis
    tsw_inletdry=0; tsw_2dry=0

    while abs(Areq/(A*(1-0.01*SAM))-1) > 0.001 and count1 < 100:
        count1 += 1
        dpt=0.001; dptlast=1.1*dpt; tmtw=(tit+tot)/2+config; count2=0

        # Inner loop: dpt convergence
        while abs(dptlast/dpt-1) > 0.001 and count2 < 100:
            count2 += 1; dptlast = dpt
            dp_arr = dPsolver(tit,tot,tmtw,Ftt,fpart,Gt,Dti,Lt,sigmat,omegai,kappa,tubetyp,config)
            dpt=dp_arr[0]; dptcount=dp_arr[2]; omegao=dp_arr[7]
            Qguess=(mdott/(1+omegai)
                    *(Cp(Ftt,fpart,tit)*tit+omegai*hgwater(tit)
                      -Cp(Ftt,fpart,tot)*tot-omegao*hgwater(tot))/1000)
            tmt=(tit+tot)/2
            tos=outlet_temp(Fts,fpars,Qguess,mdots,tis,tit,0,0,config)
            tms=(tis+tos)/2
            Res=Gs*Dto/max(mu(Fts,fpars,tms),1e-12)
            jtot=Jtotal(Res,Jc,Jl,Abas,Acs,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc)
            Gtcor=Gt*(1+0.5*(omegai+omegao))/(1+omegai)
            tw_arr=tubewall(tms,tmt,Gtcor,Res,Dto,Dti,Xt,Lt,jtot,Rt,
                            Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'wet',pattern)
            tmtw=tw_arr[0]; tmsw=tw_arr[1]; Ucount=tw_arr[3]; hs=tw_arr[5]

        # Find dry/wet boundary t2t
        t2t=tit; t2tdelta=(t2t-tot)/2; dptSF=0.0; t2s=tos
        t2tw_g=dp_dew+1; count3=0

        while abs(t2tw_g-dew_point(Ftt,fpart-dptSF/100,omegai)) > 0.01 and count3 < 100:
            count3 += 1
            if t2t < tit:
                QSF=(mdott/(1+omegai)
                     *(Cp(Ftt,fpart,tit)*tit+omegai*hgwater(tit)
                       -Cp(Ftt,fpart,t2t)*t2t-omegai*hgwater(t2t))/1000)
                t2s=outlet_temp(Fts,fpars,QSF,mdots,tos,t2t,0,0,-config)
                tms_d=(t2s+tos)/2; tmt_d=(tit+t2t)/2
                Res_d=mdots*Dto/(Acs*max(mu(Fts,fpars,tms_d),1e-12))
                tw2=tubewall(tms_d,tmt_d,Gt,Res_d,Dto,Dti,Xt,Lt,jtot,Rt,
                             Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'dry',pattern)
                tmtwdry=tw2[0]; htdry=tw2[4]; hsdry=tw2[5]; U_d=tw2[2]
                if abs(tit-tos)>1e-9 and abs(t2t-t2s)>1e-9:
                    LMTD_d=((tit-tos)-(t2t-t2s))/math.log(max((tit-tos)/(t2t-t2s),1e-9))
                    Areqdry=QSF*1000/max(U_d*LMTD_d,1e-9)
                    tsw_inletdry=U_d/hsdry*(tit-tos)+tos if hsdry>0 else 0
                    tsw_2dry=U_d/hsdry*(t2t-t2s)+t2s if hsdry>0 else 0
                else:
                    Areqdry=0; tsw_inletdry=0; tsw_2dry=0
            else:
                Areqdry=0; t2s=tos; QSF=0; tmtwdry=tit; htdry=0; hsdry=0

            dp_sf=dPsolver(tit,t2t,tmtwdry,Ftt,fpart,Gt,Dti,Lt,sigmat,omegai,kappa,tubetyp,config)
            dptSF=dp_sf[0]*Areqdry/max(A,1e-9)
            tms_w=(tis+t2s)/2; tmt_w=(t2t+tot)/2
            Res_w=mdots*Dto/(Acs*max(mu(Fts,fpars,tms_w),1e-12))
            tw3=tubewall(tms_w,tmt_w,Gtcor,Res_w,Dto,Dti,Xt,Lt,jtot,Rt,
                         Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'wet',pattern)
            ht=tw3[4]; hs=tw3[5]
            hs_eff=(hs**(-1)+Rfs)**(-1); ht_eff=(ht**(-1)+Dto*Rft/Dti)**(-1)
            ww2=wetwall_temp(Ftt,fpart-dptSF/100,omegai,Rt,hs_eff,ht_eff,t2s,t2t)
            t2tw_g=ww2[0]
            if abs(t2tw_g-dew_point(Ftt,fpart-dptSF/100,omegai)) > 0.01:
                t2t=t2t-t2tdelta if t2tw_g>dew_point(Ftt,fpart-dptSF/100,omegai) else t2t+t2tdelta
                t2tdelta /= 2

        t2t = min(t2t, tit)
        ww2=wetwall_temp(Ftt,fpart-dptSF/100,omegai,Rt,(hs**(-1)+Rfs)**(-1),(ht**(-1)+Dto*Rft/Dti)**(-1),t2s,t2t)
        t2tw=ww2[0]

        # Enthalpy LMED for wet zone
        E2t=(Cp(Ftt,fpart,t2t)*t2t+omegai*hgwater(t2t))/(1+omegai)
        Psw2=Pswater(t2tw); den2=fpart*1e5-dptSF*1000-Psw2
        omega2tw=18.015/Mw(Ftt)*Psw2/den2 if den2>0 else 0
        E2tw=(Cp(Ftt,fpart,t2tw)*t2tw+omega2tw*hgwater(t2tw))/(1+omega2tw)
        Eot=(Cp(Ftt,fpart,tot)*tot+omegao*hgwater(tot))/(1+omegao)
        wwo=wetwall_temp(Ftt,fpart-dpt/100,omegao,Rt,(hs**(-1)+Rfs)**(-1),(ht**(-1)+Dto*Rft/Dti)**(-1),tis,tot)
        totw=wwo[0]
        Pswo=Pswater(totw); deno=fpart*1e5-dpt*1000-Pswo
        omegaotw=18.015/Mw(Ftt)*Pswo/deno if deno>0 else 0
        Eotw=(Cp(Ftt,fpart,totw)*totw+omegaotw*hgwater(totw))/(1+omegaotw)
        d1=E2t-E2tw; d2=Eot-Eotw
        LMED=(d1-d2)/math.log(max(d1/d2,1e-9)) if abs(d1)>1e-9 and abs(d2)>1e-9 else max(d1,d2,1e-9)

        htmt=(ht**(-1)+Dto*Rft/Dti)**(-1)/max(Cp(Ftt,fpart,(t2t+tot)/2),1.0)
        Areqwet=(Qguess-QSF)*1000/max(htmt*LMED,1e-9)
        Areq=Areqdry+Areqwet

        if abs(Areq/(A*(1-0.01*SAM))-1) > 0.001:
            tot=tot+totdelta if Areq>A*(1-0.01*SAM) else tot-totdelta
            totdelta /= 2

    # Final quantities
    Qguess=(mdott/(1+omegai)
            *(Cp(Ftt,fpart,tit)*tit+omegai*hgwater(tit)
              -Cp(Ftt,fpart,tot)*tot-omegao*hgwater(tot))/1000)
    dT1=tit-tos; dT2=tot-tis
    if abs(dT1)>1e-9 and abs(dT2)>1e-9:
        U=Qguess*1000/max(A*(1-0.01*SAM)*((dT1-dT2)/math.log(max(dT1/dT2,1e-9))),1e-9)
    else:
        U=0.0
    Areq_s=max(Areq,1e-9)
    ht=(ht*Areqwet+htdry*Areqdry)/Areq_s
    hs=(hs*Areqwet+hsdry*Areqdry)/Areq_s
    return [Qguess,count1,U,Ucount,dpt,dptcount,t2t,t2tw,totw,0,
            tmtw,tmsw,Areqdry,ht,hs,htmt,LMED,tsw_inletdry,tsw_2dry,ww2[2],wwo[2]]
