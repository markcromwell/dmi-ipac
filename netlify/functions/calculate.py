"""
DMI IPAC / WCAC Heat Exchanger Calculation Engine
Faithful Python translation of VBA Module1-4 from W1279 DMI WCAC Design program I0-1.xlsm

Fluid codes:  g-01=Air  g-02=Ar  g-03=CO2  g-04=CO  g-05=He
              g-06=H2   g-07=CH4 g-08=N2   g-09=O2
              l-10=Water  l-11=Water/EG  l-12=Water/PG  l-13=Sea water

config convention: +1 = heat flow from shell to tubes; -1 = from tubes to shell.
Aftercooler (hot gas cooled by water) → config = -1.
"""
from http.server import BaseHTTPRequestHandler
import json, math

# ── MODULE 1: FLUID PROPERTIES ────────────────────────────────────────────────

def _Findex(Ft):
    return int(Ft[-2:])

def Mw(Ft):
    """Molecular weight, kg/kmol"""
    return {1:28.96,2:39.948,3:44.01,4:28.01,5:4.003,
            6:2.02,7:16.043,8:28.013,9:31.999}.get(_Findex(Ft),28.96)

# Water (0.01–300°C, Rogers & Mayhew)
def rho_water(t):
    if t<=120: return 1000+0.0095578*t-0.0056262*t**2+0.000013354*t**3
    return 792.97+4.3331*t-0.038282*t**2+0.00012268*t**3-0.0000001539*t**4
def Cp_water(t):
    if t<=25.15:  return 4221.7-4.263*t+0.15911*t**2-0.0021464*t**3
    if t<=44.89:  return 4213.2-1.9994*t+0.028563*t**2
    if t<=120:    return 4198.6-0.91885*t+0.012116*t**2-0.000008545*t**3
    return 3091.8+19.231*t-0.11065*t**2+0.00024882*t**3
def K_water(t):
    if t<=120: return 0.5688+0.0018959*t-0.000008626*t**2+0.0000000086192*t**3
    return (595.23+1.3658*t-0.0048449*t**2-0.0000016765*t**3+0.0000000021291*t**4)*0.001
def mu_water(t):
    if t<=120: return (0.0017487-0.000053635*t+0.0000010181*t**2-0.000000011676*t**3
                       +0.000000000071805*t**4-1.7918e-13*t**5)
    return (769.87-8.1453*t+0.040941*t**2-0.000099534*t**3+0.000000094652*t**4)*1e-6
def Pr_water(t):
    if t<=47.16: return 12.96-0.4528*t+0.0098052*t**2-0.00012467*t**3+0.00000068414*t**4
    if t<=120:   return 10.3552-0.2379*t+0.0027172*t**2-0.000015588*t**3+0.000000035778*t**4
    return 4.9209-0.054892*t+0.00029412*t**2-0.00000076479*t**3+0.00000000082274*t**4

def Pswater(t):
    """IAPWS-IF97: saturation pressure, Pa. Valid 0–373.946°C."""
    if not (0 < t < 373.946): return 0.0
    xi = (273.15+t) - 0.23855557567849/(273.15+t-650.17534844798)
    A = xi**2 + 1167.0521452767*xi - 724213.16703206
    B = -17.073846940092*xi**2 + 12020.82470247*xi - 3232555.0322333
    C = 14.91510861353*xi**2 - 4823.2657361591*xi + 405113.40542057
    return 1e5*10*(2*C/(-B+(B**2-4*A*C)**0.5))**4

def Cpgwater(t):
    """Cp of saturated water vapour, J/kg.K, 0.01–300°C"""
    return math.exp(7.533-0.0001017*t+0.000005191*t**2+0.00000003669*t**3-0.00000000003143*t**4)

def hgwater(t):
    """Enthalpy of saturated water vapour, J/kg, 0.01–300°C"""
    return 2503000+1660*t+2.465*t**2-0.01745*t**3

def hfwater(t):
    """Enthalpy of saturated water, J/kg"""
    if t<10: return 4166.81*t-41.66
    return -1263+4306*t-1.785*t**2+0.007925*t**3

# Water/Ethylene Glycol (phi = volume %, 20–60%)
def _glycol_interp(phi, t, A, B, C=None, D=None, log10=False, e=None, f=None):
    phimin = 10*int(phi/10)
    i = phimin//10 - 2
    def poly(idx):
        v = A[idx]+B[idx]*t
        if C: v += C[idx]*t**2
        if D: v += D[idx]*t**3
        if e: v += e[idx]*t**4
        if f: v += f[idx]*t**5
        return v
    p1,p2 = poly(i),poly(i+1)
    if log10: return 0.001*10**((p1-p2)/10*(phimin-phi)+p1)
    return (p1-p2)/10*(phimin-phi)+p1

def rho_weg(phi,t):
    A=[1035.7,1051.8,1066.8,1081.1,1094.6,1094.6]; B=[-0.24864,-0.27774,-0.30738,-0.33814,-0.36982,-0.36982]; C=[-0.002432,-0.0024316,-0.0024322,-0.0024322,-0.0024325,-0.0024325]
    return _glycol_interp(phi,t,A,B,C)
def Cp_weg(phi,t):
    A=[3768.7,3588.6,3401,3203.4,2996.6,2996.6]; B=[2.3,2.8367,3.3556,3.8616,4.3656,4.3656]
    return _glycol_interp(phi,t,A,B)
def k_weg(phi,t):
    A=[0.46537,0.42323,0.38634,0.35235,0.32248,0.32248]; B=[0.0014692,0.0012086,0.00096925,0.00075705,0.00059195,0.00059195]; C=[-0.0000066581,-0.0000052883,-0.000004135,-0.0000027201,-0.0000021225,-0.0000021225]; D=[0.0000000035498,0.0000000015871,0.00000000040636,-0.0000000035095,-0.0000000029294,-0.0000000029294]
    return _glycol_interp(phi,t,A,B,C,D)
def mu_weg(phi,t):
    A=[0.48066,0.61817,0.76569,0.90592,1.081,1.081]; B=[-0.015396,-0.015999,-0.017365,-0.018112,-0.019919,-0.019919]; C=[0.00012696,0.00012626,0.00015893,0.00015788,0.00012939,0.00012939]; D=[-0.0000007509,-0.0000010258,-0.0000015288,-0.0000016299,-0.00000067045,-0.00000067045]; e=[0.0000000013354,0.0000000058645,0.0000000093007,0.000000011197,0.000000001735,0.000000001735]; f=[3.7932e-12,-0.000000000015174,-0.000000000023904,-0.000000000031769,0,0]
    return _glycol_interp(phi,t,A,B,C,D,log10=True,e=e,f=f)
def Pr_weg(phi,t): return Cp_weg(phi,t)*mu_weg(phi,t)/k_weg(phi,t)

# Water/Propylene Glycol (phi = volume %, 20–60%)
def rho_wpg(phi,t):
    A=[1025.8,1036.2,1045.1,1052.7,1059,1059]; B=[-0.28997,-0.3434,-0.39263,-0.44037,-0.48682,-0.48682]; C=[-0.0025219,-0.0025508,-0.0025719,-0.002567,-0.0025332,-0.0025332]
    return _glycol_interp(phi,t,A,B,C)
def Cp_wpg(phi,t):
    A=[3928.9,3792.9,3635.7,3454.7,3250.3,3250.3]; B=[2.1838,2.7515,3.3014,3.8585,4.4133,4.4133]
    return _glycol_interp(phi,t,A,B)
def k_wpg(phi,t):
    A=[0.45613,0.40923,0.36646,0.32714,0.29116,0.29116]; B=[0.0014752,0.0012111,0.00098259,0.00076193,0.00058192,0.00058192]; C=[-0.0000065974,-0.0000052474,-0.0000042594,-0.000003036,-0.0000021872,-0.0000021872]; D=[0.0000000022672,0.00000000051086,0,-0.0000000024418,-0.0000000041292,-0.0000000041292]
    return _glycol_interp(phi,t,A,B,C,D)
def mu_wpg(phi,t):
    A=[0.60746,0.84959,1.0908,1.262,1.4974,1.4974]; B=[-0.017258,-0.02083,-0.025228,-0.02553,-0.028049,-0.028049]; C=[0.00011735,0.00014517,0.000207,0.00019379,0.00018028,0.00018028]; D=[-0.00000054263,-0.00000061911,-0.0000011071,-0.000001077,-0.0000005914,-0.0000005914]; e=[0.000000001176,0.0000000012373,0.0000000027871,0.0000000040806,0.00000000063291,0.00000000063291]; f=[0,0,0,-0.000000000007841,0,0]
    return _glycol_interp(phi,t,A,B,C,D,log10=True,e=e,f=f)
def Pr_wpg(phi,t): return Cp_wpg(phi,t)*mu_wpg(phi,t)/k_wpg(phi,t)

# Sea water 35g/kg, 10–120°C (HEDH 1992, ESDU 77024)
def rhosea(t):  return 1028.8-0.1789*t-2.637e-3*t**2
def Cpsea(t):   return 3992-5.033e-2*t+6.071e-3*t**2
def ksea(t):    return 0.5667+1.775e-3*t-6.504e-6*t**2
def musea(t):   return (0.9716+2.268*math.log10(t)-2.401*math.log10(t)**2+0.551*math.log10(t)**3)*1e-3
def Prsea(t):   return 13.09-0.4026*t+6.317e-3*t**2-4.784e-5*t**3+1.386e-7*t**4

# Air, -100–425°C low pressure (Rogers & Mayhew)
def rho_air(p,t):  return p*1e5/(8314.4/28.96*(273.15+t))
def Cp_air(t):     return 1003.716+0.035384*t+0.00028394*t**2+0.00000049078*t**3-0.0000000010188*t**4
def K_air(t):      return 0.024131+0.000079649*t-0.000000038441*t**2+0.000000000015891*t**3
def mu_air(t):     return 0.000017161+0.000000049069*t-0.000000000042916*t**2+5.1084e-14*t**3-3.5316e-17*t**4
def Pr_air(t):     return 0.7137-0.00026517*t+0.0000005083*t**2+0.00000000026031*t**3-8.8693e-13*t**4

# Argon, 0–1200°C (HEDH)
def rho_ar(p,t):  return p*1e5/(8314.4/39.948*(273.15+t))
def Cp_ar(t):     return 521.0
def K_ar(t):      return 0.01641+5.153e-5*t-2.818e-8*t**2+1.095e-11*t**3
def mu_ar(t):     return (21.13+0.06284*t-2.855e-5*t**2+9.442e-9*t**3)*1e-6
def Pr_ar(t):     return Cp_ar(t)*mu_ar(t)/K_ar(t)

# CO2, 0–1200°C (HEDH)
def rho_co2(p,t): return p*1e5/(8314.4/44.01*(273.15+t))
def Cp_co2(t):    return 819.9+1.001*t-7.455e-4*t**2+2.15e-7*t**3
def K_co2(t):     return (14.56+0.08244*t+7.559e-7*t**2-9.113e-9*t**3)*1e-3
def mu_co2(t):    return (13.68+0.05047*t-2.213e-5*t**2+6.235e-9*t**3)*1e-6
def Pr_co2(t):    return Cp_co2(t)*mu_co2(t)/K_co2(t)

# CO, 0–1200°C (HEDH)
def rho_co(p,t):  return p*1e5/(8314.4/28.01*(273.15+t))
def Cp_co(t):     return 1037+0.0761*t+3.077e-4*t**2-1.868e-7*t**3
def K_co(t):      return (22.94+0.07273*t-8.923e-6*t**2)*1e-3
def mu_co(t):     return (16.79+0.04506*t-1.792e-5*t**2+4.321e-9*t**3)*1e-6
def Pr_co(t):     return Cp_co(t)*mu_co(t)/K_co(t)

# Helium, -150–1200°C (HEDH)
def rho_he(p,t):  return p*1e5/(8314.4/4.003*(273.15+t))
def Cp_he(t):     return 5200.0
def K_he(t):      return (144.3+0.3812*t-0.0001696*t**2+6.975e-8*t**3)*1e-3
def mu_he(t):     return (18.54+0.04708*t-1.728e-5*t**2+6.095e-9*t**3)*1e-6
def Pr_he(t):     return Cp_he(t)*mu_he(t)/K_he(t)

# Hydrogen, 0–1200°C (HEDH)
def rho_h2(p,t):  return p*1e5/(8314.4/2.02*(273.15+t))
def Cp_h2(t):     return 14210+2.57*t-0.007258*t**2+9.736e-6*t**3-3.728e-9*t**4
def K_h2(t):      return 0.1673+0.000514*t-3.06e-7*t**2+1.768e-10*t**3
def mu_h2(t):     return (8.5+0.01805*t-2.423e-6*t**2)*1e-6
def Pr_h2(t):     return Cp_h2(t)*mu_h2(t)/K_h2(t)

# Methane, 0–1200°C (HEDH)
def rho_ch4(p,t): return p*1e5/(8314.4/16.043*(273.15+t))
def Cp_ch4(t):    return 2135+3.492*t+1.287e-7*t**2-6.671e-10*t**3
def K_ch4(t):     return (31.01+0.1463*t+9.642e-5*t**2-4.974e-8*t**3)*1e-3
def mu_ch4(t):    return (10.26+0.03108*t-1.319e-5*t**2+3.976e-9*t**3)*1e-6
def Pr_ch4(t):    return Cp_ch4(t)*mu_ch4(t)/K_ch4(t)

# Nitrogen, 0–1200°C (HEDH)
def rho_n2(p,t):  return p*1e5/(8314.4/28.013*(273.15+t))
def Cp_n2(t):     return 1038+0.01388*t+3.736e-4*t**2-2.073e-7*t**3
def K_n2(t):      return (24.12+0.0688*t-6.378e-6*t**2)*1e-3
def mu_n2(t):     return (17.02+0.04023*t-8.685e-6*t**2)*1e-6
def Pr_n2(t):     return Cp_n2(t)*mu_n2(t)/K_n2(t)

# Oxygen, 0–1200°C (HEDH)
def rho_o2(p,t):  return p*1e5/(8314.4/31.999*(273.15+t))
def Cp_o2(t):     return 910.7+0.2865*t-1.119e-5*t**2-5.787e-8*t**3
def K_o2(t):      return (24.5+0.08377*t-1.341e-5*t**2)*1e-3
def mu_o2(t):     return (19.75+0.04735*t-9.637e-6*t**2)*1e-6
def Pr_o2(t):     return Cp_o2(t)*mu_o2(t)/K_o2(t)

# Dispatch functions (VBA: rho/Cp/K/mu/Pr)
def rho(Ft, fpar, t):
    i = _Findex(Ft)
    return [0,rho_air,rho_ar,rho_co2,rho_co,rho_he,rho_h2,rho_ch4,rho_n2,rho_o2,
            lambda p,t:rho_water(t), None,None, lambda p,t:rhosea(t)][i](fpar,t)
def Cp(Ft, fpar, t):
    i = _Findex(Ft)
    return [0,Cp_air,Cp_ar,Cp_co2,Cp_co,Cp_he,Cp_h2,Cp_ch4,Cp_n2,Cp_o2,
            Cp_water,None,None,Cpsea][i](t) if i!=11 and i!=12 else (Cp_weg(fpar,t) if i==11 else Cp_wpg(fpar,t))
def K(Ft, fpar, t):
    i = _Findex(Ft)
    return [0,K_air,K_ar,K_co2,K_co,K_he,K_h2,K_ch4,K_n2,K_o2,
            K_water,None,None,ksea][i](t) if i!=11 and i!=12 else (k_weg(fpar,t) if i==11 else k_wpg(fpar,t))
def mu(Ft, fpar, t):
    i = _Findex(Ft)
    return [0,mu_air,mu_ar,mu_co2,mu_co,mu_he,mu_h2,mu_ch4,mu_n2,mu_o2,
            mu_water,None,None,musea][i](t) if i!=11 and i!=12 else (mu_weg(fpar,t) if i==11 else mu_wpg(fpar,t))
def Pr(Ft, fpar, t):
    i = _Findex(Ft)
    return [0,Pr_air,Pr_ar,Pr_co2,Pr_co,Pr_he,Pr_h2,Pr_ch4,Pr_n2,Pr_o2,
            Pr_water,None,None,Prsea][i](t) if i!=11 and i!=12 else (Pr_weg(fpar,t) if i==11 else Pr_wpg(fpar,t))


# ── MODULE 2: SURFACE PERFORMANCE ────────────────────────────────────────────

def fcp_plaintube(Re, L, D, kappa):
    """Thermatec plain-tube Fanning friction factor (constant fluid properties)"""
    fRe,K_,C = 16.0, 1.25, 0.00021
    xcross = L/(D*Re) if Re>0 else 1e9
    flam = (1/Re)*(3.44/xcross**0.5 + (K_/(4*xcross)+fRe-3.44*xcross**(-0.5))/(1+C*xcross**(-2)))
    if Re>100:
        fA = -2*math.log10(kappa/(3.7*D)+12/Re)
        fB = -2*math.log10(kappa/(3.7*D)+2.51*fA/Re)
        fC = -2*math.log10(kappa/(3.7*D)+2.51*fB/Re)
        fturb = 0.065*D/(4*L)+0.25*(fA-(fB-fA)**2/(fC-2*fB+fA))**(-2)
    else:
        fturb = 0.0
    if L/(2500*D) > 0.01:
        blend = max(0.0, 1-((xcross-0.01)/(L/(D*2500)-0.01))**3)
    else:
        blend = 0.0
    fdelta = max(0.0, fturb-flam)
    ftrans = flam+fdelta*blend**6
    if xcross > 0.01:
        return ftrans
    return fturb if fturb>flam else flam

def Nu_plaintube(Re, f, Pr_, L, D, fpcorr):
    """Thermatec plain-tube Nusselt number"""
    Nufd = 3.66
    Nulowturb  = math.exp(-3.796+0.795*math.log(Re)+0.495*math.log(Pr_)-0.0225*math.log(Pr_)**2)
    Nuhighturb = (f/2*(Re-1000)*Pr_)/(1+12.7*(f/2)**0.5*(Pr_**(2/3)-1))
    Nuturb = max(Nulowturb, Nuhighturb)
    Re_lam = min(Re, 2300.0)
    Nulam = Nufd+0.0677*(Re_lam*Pr_*D/L)**1.33/(1+0.1*Pr_*(Re_lam*D/L)**0.3)
    Nutrans = Nulam*math.exp((Re-2200)/730)
    Nuturbcorr = Nuturb*fpcorr
    return (Nulam**10+(Nutrans**(-2)+Nuturbcorr**(-2))**(-5))**0.1

def h_tube(Re, Dto, Dti, L, tm, tw, Ft, fpar, kappa, tubetyp, config, condition):
    """Tube-side HTC referred to Dto. condition='dry'|'wet'"""
    if Ft[0]=='g':
        nfp = 0.47 if config==1 else 0.0
        fpcorr = ((273.15+tm)/(273.15+tw))**nfp
    else:
        nfp = 0.11 if config==1 else 0.25
        fpcorr = (mu(Ft,fpar,tm)/mu(Ft,fpar,tw))**nfp
    if tubetyp[0].upper()=='P':
        f = fcp_plaintube(Re,L,Dti,kappa)
        h = K(Ft,fpar,tm)/Dto*Nu_plaintube(Re,f,Pr(Ft,fpar,tm),L,Dti,fpcorr)
        if condition=='wet': h *= 10**(0.1102-1.367e-7*Re)
    else:
        # Grooved tube — Wcool ACTUBE data, 6800<Re<157700
        if condition=='dry':
            Nu = ((0.007905*Re**0.9537)**80+(0.04427*Re**0.8)**80)**(1/80)*Pr(Ft,fpar,tm)**0.3
        else:
            Nu = ((0.01198*Re**0.9384)**80+(0.07627*Re**0.7723)**80)**(1/80)*Pr(Ft,fpar,tm)**0.3
        h = K(Ft,fpar,tm)/Dto*Nu
    return h

def f_tube(Re, L, Dti, kappa, Ft, fpar, tm, tw, tubetyp, config):
    """Tube-side friction factor (Fanning). Returns (f, cfp_corr)."""
    if tubetyp[0].upper()=='P':
        if Ft[0]=='g':
            if Re>=4000:   m=-0.1
            elif config==-1: m=0.81
            else:           m=0.0
            cfp_corr=((273.15+tw)/(273.15+tm))**m
        else:
            if Re>=4000:   m=0.24 if config==-1 else 0.25
            else:          m=0.54 if config==-1 else 0.58
            cfp_corr=(mu(Ft,fpar,tw)/mu(Ft,fpar,tm))**m
        f=fcp_plaintube(Re,L,Dti,kappa)*cfp_corr
    else:
        cfp_corr=1.0
        f=0.2478*Re**(-0.135)   # grooved tube, Wcool
    return f, cfp_corr

def f_shell(Re, D, Xt, pattern):
    """Bell-Taborek shell-side Fanning friction factor"""
    if not (0.005<=D<0.055): return 0.0
    if pattern=='RS':
        if Re<10:      b1,b2=32,-1
        elif Re<100:   b1,b2=26.2,-0.913
        elif Re<1000:  b1,b2=3.5,-0.476
        elif Re<10000: b1,b2=0.333,-0.136
        else:          b1,b2=0.303,-0.126
        return b1*(1.33*D/(0.7071*Xt))**(6.59/(1+0.14*Re**0.52))*Re**b2
    elif pattern=='S':
        if Re<10:      b1,b2=35,-1
        elif Re<100:   b1,b2=32.1,-0.963
        elif Re<1000:  b1,b2=6.09,-0.602
        elif Re<10000: b1,b2=0.0815,0.022
        else:          b1,b2=0.391,-0.148
        return b1*(1.33*D/Xt)**(6.3/(1+0.14*Re**0.378))*Re**b2
    else:  # T
        if Re<10:      b1,b2=48,-1
        elif Re<100:   b1,b2=45.1,-0.973
        elif Re<1000:  b1,b2=4.57,-0.476
        elif Re<10000: b1,b2=0.486,-0.152
        else:          b1,b2=0.372,-0.123
        return b1*(1.33*D/Xt)**(7/(1+0.14*Re**0.5))*Re**b2

def j_shell(Re, D, Xt, pattern):
    """Bell-Taborek shell-side Colburn j-factor"""
    if not (0.005<=D<0.055): return 0.0
    if pattern=='RS':
        if Re<10:    a1,a2=1.55,-0.667
        elif Re<100: a1,a2=1.498,-0.656
        elif Re<1000:a1,a2=0.73,-0.5
        else:        a1,a2=0.37,-0.396
        return a1*(1.33*D/(0.7071*Xt))**(1.93/(1+0.14*Re**0.5))*Re**a2
    elif pattern=='S':
        if Re<10:    a1,a2=0.97,-0.667
        elif Re<100: a1,a2=0.9,-0.631
        elif Re<1000:a1,a2=0.408,-0.46
        elif Re<10000:a1,a2=0.107,-0.266
        else:        a1,a2=0.37,-0.395
        return a1*(1.33*D/Xt)**(1.187/(1+0.14*Re**0.37))*Re**a2
    else:  # T
        if Re<10:    a1,a2=1.4,-0.667
        elif Re<100: a1,a2=1.36,-0.657
        elif Re<1000:a1,a2=0.593,-0.477
        else:        a1,a2=0.321,-0.388
        return a1*(1.33*D/Xt)**(1.45/(1+0.14*Re**0.519))*Re**a2

def KcKe(Re, D, L, sigma):
    """Kays-London Kc/Ke for multiple round channels. Returns (Kc,Ke)."""
    xplus_opt=[20,0.2,0.1,0.05]; Re_opt=[3000,5000,10000,1000000]; sigma_opt=[0.2,0.37,0.54]
    kc_opt=[0.994,0.983,0.926,0.8, 0.456,0.443,0.426,0.329, 0.925,0.912,0.858,0.734, 0.385,0.371,0.356,0.259, 0.857,0.843,0.792,0.666, 0.32,0.305,0.288,0.193]
    ke_opt=[0.517,0.517,0.517,0.554, 0.614,0.614,0.629,0.643, 0.158,0.158,0.183,0.232, 0.357,0.357,0.37,0.406, -0.143,-0.134,-0.105,-0.039, 0.151,0.159,0.167,0.209]
    xp = 4*L/(D*Re) if Re>0 else 1e9
    sigma_ind=1
    while sigma_ind>0 and sigma<sigma_opt[sigma_ind]: sigma_ind-=1
    Re_ind=2
    while Re_ind>0 and Re<Re_opt[Re_ind]: Re_ind-=1
    xplus_ind=2
    while xplus_ind>0 and xp>=xplus_opt[xplus_ind]: xplus_ind-=1
    def interp1d(a,x,x0,x1): return (a[0]-a[1])/(x0-x1)*(x-x1)+a[1]
    if Re<3000:
        i1=xplus_ind+8*sigma_ind; i2=xplus_ind+8*(sigma_ind+1)
        if 0.05<=xp<=20:
            kc1=interp1d([kc_opt[i1],kc_opt[i1+1]],xp,xplus_opt[xplus_ind],xplus_opt[xplus_ind+1])
            kc2=interp1d([kc_opt[i2],kc_opt[i2+1]],xp,xplus_opt[xplus_ind],xplus_opt[xplus_ind+1])
            ke1=interp1d([ke_opt[i1],ke_opt[i1+1]],xp,xplus_opt[xplus_ind],xplus_opt[xplus_ind+1])
            ke2=interp1d([ke_opt[i2],ke_opt[i2+1]],xp,xplus_opt[xplus_ind],xplus_opt[xplus_ind+1])
        elif xp>20:
            kc1,kc2,ke1,ke2=kc_opt[i1],kc_opt[i2],ke_opt[i1],ke_opt[i2]
        else:
            kc1,kc2,ke1,ke2=kc_opt[i1+1],kc_opt[i2+1],ke_opt[i1+1],ke_opt[i2+1]
    else:
        i1=4+Re_ind+8*sigma_ind; i2=4+Re_ind+8*(sigma_ind+1)
        if Re<=1000000:
            kc1=interp1d([kc_opt[i1],kc_opt[i1+1]],Re,Re_opt[Re_ind+1],Re_opt[Re_ind])
            kc2=interp1d([kc_opt[i2],kc_opt[i2+1]],Re,Re_opt[Re_ind+1],Re_opt[Re_ind])
            ke1=interp1d([ke_opt[i1],ke_opt[i1+1]],Re,Re_opt[Re_ind+1],Re_opt[Re_ind])
            ke2=interp1d([ke_opt[i2],ke_opt[i2+1]],Re,Re_opt[Re_ind+1],Re_opt[Re_ind])
        else:
            kc1,kc2,ke1,ke2=kc_opt[i1+1],kc_opt[i2+1],ke_opt[i1+1],ke_opt[i2+1]
    if 0.2<=sigma<=0.54:
        Kc=interp1d([kc1,kc2],sigma,sigma_opt[sigma_ind],sigma_opt[sigma_ind+1])
        Ke=interp1d([ke1,ke2],sigma,sigma_opt[sigma_ind],sigma_opt[sigma_ind+1])
    elif sigma>0.54:
        Kc,Ke=kc2,ke2
    else:
        Kc,Ke=kc1,ke1
    return Kc, Ke


# ── MODULE 3: THERMAL PERFORMANCE CALCULATIONS ───────────────────────────────

def dew_point(Ft, fpar, omega):
    """Gas dew point, °C. fpar in bara."""
    if omega<=0: return -273.15
    Ps = omega*fpar*1e5/(18.015/Mw(Ft)+omega)
    td=373.0; tdelta=186.795; count=0
    while count<1000:
        Psw=Pswater(td)
        if abs(Psw-Ps)<=1: break
        td = td-tdelta if Psw>Ps else td+tdelta
        tdelta/=2; count+=1
    if td<0.01 or td>373: return -273.15
    return td

def outlet_temp(Ft, fpar, Q, mdot, ti, tomax, dp, omegai, config):
    """Outlet temperature given Q (kW). config: +1=shell heated, -1=tube cooled."""
    t=tomax; tlast=ti; count=0
    if Ft[0]=='l':
        while abs(t-tlast)>0.0001 and count<100:
            count+=1; tlast=t
            t=ti-Q*1000*config/(mdot*Cp(Ft,fpar,(ti+t)/2))
    else:
        tdelta=ti-t
        while abs(t-tlast)>0.0001 and count<100:
            count+=1; tlast=t; tdelta/=2
            t=max(t,0.01)
            Psw=Pswater(t)
            if t<=0.01: omegao=0.0
            else:
                denom=fpar*1e5-dp*1000-Psw
                omegao=18.015/Mw(Ft)*Psw/denom if denom>0 else omegai
                if omegai<omegao or omegao<0: omegao=omegai
            Qguess=mdot/(1+omegai)*(Cp(Ft,fpar,ti)*ti+omegai*hgwater(ti)-Cp(Ft,fpar,t)*t-omegao*hgwater(t))*config/1000
            t=t+tdelta if Qguess>Q else t-tdelta
            t=max(t,0.01)
    return t

def wetwall_temp(Ft, fpar, omega, Rt, hs, ht, ts, tt):
    """Tube wall temp in wet zone (McQuiston method). Returns (tw, count, tsw)."""
    tw=0.5*(tt+ts); tdelta=(tt-ts)/4
    Eb=(Cp(Ft,fpar,tt)*tt+omega*hgwater(tt))/(1+omega)
    count=0
    for _ in range(100):
        Psw=Pswater(tw); denom=fpar*1e5-Psw
        omegaw=18.015/Mw(Ft)*Psw/denom if denom>0 else 0.0
        Ew=Cp(Ft,fpar,tw)*tw+omegaw*hgwater(tw)
        lhs=(Rt+hs**(-1))**(-1)*(tw-ts)
        rhs=ht/Cp(Ft,fpar,tt)*(Eb-Ew/(1+omegaw))  # note: Ew is not divided by (1+omegaw) in VBA line 1185
        # VBA line 1185: Ew = Cp*tw + omega_w*hg(tw)  (not divided)
        # VBA convergence check line 1176 uses same Ew
        if abs(lhs/rhs-1)<=0.001: break
        tw=tw-tdelta if lhs>rhs else tw+tdelta
        tdelta/=2; count+=1
    Psw=Pswater(tw); denom2=fpar*1e5-Psw
    omegaw=18.015/Mw(Ft)*Psw/denom2 if denom2>0 else 0.0
    Ew=(Cp(Ft,fpar,tw)*tw+omegaw*hgwater(tw))/(1+omegaw)
    tsw=(ht/Cp(Ft,fpar,tt)*(Eb-Ew))/hs+ts
    return tw, count, tsw

def h_shell(Re, tb, tw, D, Xt, jtot, Ft, fpar, config, pattern):
    """Shell-side heat transfer coefficient (constant properties × correction × jtot)"""
    if Ft[0]=='g':
        nfp=0.25 if config==-1 else 0.0
        fpcorr=((273.15+tb)/(273.15+tw))**nfp
    else:
        fpcorr=(mu(Ft,fpar,tb)/mu(Ft,fpar,tw))**0.14
    return j_shell(Re,D,Xt,pattern)*Re*Pr(Ft,fpar,tb)**(1/3)*(K(Ft,fpar,tb)/D)*jtot*fpcorr

def Jtotal(Re, Jc, Jl, Abas, Acs, Nss, Ntcc, Ntcw, Nb, Lbe, Lbc):
    """Bell-Taborek total correction factor Jtot = Jc*Jl*Jb*Jr*Js"""
    if Re>=100:
        cbh=1.25; N=0.6; Jr=1.0
    else:
        cbh=1.35; N=1/3
        Jrmax=(10/((Ntcc+Ntcw)*(Nb+1)))**0.18
        Jr=Jrmax if Re<=20 else Jrmax+(20-Re)/80*(Jrmax-1)
    Jb1=math.exp(-cbh*Abas/Acs*(1-(2*Nss/Ntcc)**(1/3))) if Ntcc>0 else 1.0
    Jb=min(Jb1,1.0)
    x=Lbe/Lbc
    Js=((Nb-1)+2*x**(1-N))/((Nb-1)+2*x)
    return Jc*Jl*Jb*Jr*Js

def tubewall(tms, tmt, Gt, Res, Dto, Dti, Xt, Lt, jtot, Rt, Ftt, Fts, fpart, fpars, Rfs, Rft, kappa, tubetyp, config, condition, pattern):
    """Iterate to converged tube wall temperatures and U. Returns (twi,two,U,count,ht,hs)."""
    twi=tmt; two=tms
    Ret=Gt*Dti/max(mu(Ftt,fpart,tmt),1e-12)
    ht=h_tube(Ret,Dto,Dti,Lt,tmt,twi,Ftt,fpart,kappa,tubetyp,config,condition)
    hs=h_shell(Res,tms,two,Dto,Xt,jtot,Fts,fpars,config,pattern)
    U=(hs**(-1)+Rfs+Rt+Dto*Rft/Dti+ht**(-1))**(-1)
    Ulast=1.05*U; count=0
    for _ in range(100):
        if abs(U/Ulast-1)<=0.001: break
        Ulast=U
        twi=tmt+U/(ht**(-1)+Dto*Rft/Dti)**(-1)*(tms-tmt)
        two=tms-U/(hs**(-1)+Rfs)**(-1)*(tms-tmt)
        ht=h_tube(Ret,Dto,Dti,Lt,tmt,twi,Ftt,fpart,kappa,tubetyp,config,condition)
        hs=h_shell(Res,tms,two,Dto,Xt,jtot,Fts,fpars,config,pattern)
        U=(hs**(-1)+Rfs+Rt+Dto*Rft/Dti+ht**(-1))**(-1)
        count+=1
    return twi,two,U,count,ht,hs

def dPsolver(t_i, t_o, tw, Ft, fpar, G, D, L, sigma, omegai, kappa, tubetyp, config):
    """Tube-side pressure drop (kPa), iterating for density change."""
    Re=G*D/max(mu(Ft,fpar,0.5*(t_i+t_o)),1e-12)
    f,_=f_tube(Re,L,D,kappa,Ft,fpar,0.5*(t_i+t_o),tw,tubetyp,config)
    rho_i=rho(Ft,fpar,t_i)*(1+omegai)/(1+(Mw(Ft)/18.015)*omegai)
    rho_o=rho(Ft,fpar,t_o)*(1+omegai)/(1+(Mw(Ft)/18.015)*omegai)
    rho_m=0.5*(rho_i+rho_o)
    dP=G**2/(2000*rho_m)*(4*L*f/D)
    dPlast=dP*1.1; omegao=omegai; Kc=0.0; Ke=0.0; count=0
    for _ in range(100):
        if abs(dP/dPlast-1)<=0.001: break
        dPlast=dP
        Po=max(fpar-dP/100, 1e-5)
        Psw=Pswater(t_o); denom=Po*1e5-Psw
        omegao=18.015/Mw(Ft)*Psw/denom if denom>0 else omegai
        if omegai<omegao or omegao<0: omegao=omegai
        rho_o=rho(Ft,Po,t_o)*(1+omegao)/(1+(Mw(Ft)/18.015)*omegao)
        rho_m=0.5*(rho_i+rho_o)
        Gcor=G*(1+0.5*(omegai+omegao))/(1+omegai)
        Re2=Gcor*D/max(mu(Ft,fpar,0.5*(t_i+t_o)),1e-12)
        f,cfp=f_tube(Re2,L,D,kappa,Ft,fpar,0.5*(t_i+t_o),tw,tubetyp,config)
        if tubetyp[0].upper()=='P':
            Kc,Ke=KcKe(Re2,D,L,sigma)
            dP=Gcor**2/(2000*rho_i)*((1-sigma**2+Kc)+4*L*f/D*(rho_i/rho_m)+2*(rho_i/rho_o-1)-(1-sigma**2-Ke)*rho_i/rho_o)
        else:
            # 0.8x correction added I0-1 250529 for Wcool consistency
            dP=0.8*Gcor**2/(2000*rho_m)*(4*L*f/D)
        count+=1
    return dP, dPlast, count, f, 1.0, Kc, Ke, omegao

def QsolverSP(tit,tis,config,Ftt,Fts,fpart,fpars,mdots,mdott,omegai,Act,Acs,A,SAM,Rfs,Rft,Dto,Dti,Lt,Xt,Jc,Jl,Abas,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc,kappa,Rt,tubetyp,pattern):
    """Single-phase Q solver (NTU-effectiveness). Returns array matching VBA QsolverSP."""
    Gt=mdott/Act; Gs=mdots/Acs
    tot=tis+tit/2
    Qguess=mdott/(1+omegai)*((Cp(Ftt,fpart,tit)*tit-Cp(Ftt,fpart,tot)*tot)+omegai*(hgwater(tit)-hgwater(tot)))/1000
    Qguesslast=Qguess*1.1; count=0; U=0; twi=tit; two=tis; ht=0; hs=0
    for _ in range(100):
        if abs(Qguesslast/Qguess-1)<=0.001: break
        Qguesslast=Qguess; count+=1
        tot=outlet_temp(Ftt,fpart,Qguess,mdott,tit,tis,0,omegai,-1*config)
        tmt=(tit+tot)/2
        Ct=abs(Qguess*1000/max(tit-tot,1e-9))
        tos=outlet_temp(Fts,fpars,Qguess,mdots,tis,tit,0,0,config)
        tms=(tis+tos)/2
        Cs=mdots*Cp(Fts,fpars,tms)
        Res=Gs*Dto/max(mu(Fts,fpars,tms),1e-12)
        jtot=Jtotal(Res,Jc,Jl,Abas,Acs,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc)
        twi,two,U,Ucount,ht,hs=tubewall(tms,tmt,Gt,Res,Dto,Dti,Xt,Lt,jtot,Rt,Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'dry',pattern)
        Cmax=max(Ct,Cs); Cmin=min(Ct,Cs); R=Cmin/Cmax
        NTU=U*A*(1-0.01*SAM)/Cmin
        Eff=(1-math.exp(-NTU*(1-R)))/(1-R*math.exp(-NTU*(1-R)))
        Qguess=Eff*Cmin/1000*(tis-tit)*config
    return [Qguess,Qguesslast,count,twi,two,U,Ucount,ht,hs,0,0]

def Qsolver(tit,tis,config,Ftt,Fts,fpart,fpars,mdots,mdott,omegai,Act,Acs,A,SAM,Rfs,Rft,Dto,Dti,Lt,sigmat,Xt,Jc,Jl,Abas,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc,kappa,Rt,tubetyp,pattern):
    """
    Two-zone (dry + wet condensing) heat transfer solver.
    Faithful translation of VBA Qsolver from Module3.bas.
    Returns array: [Q_kW, Qcount, U, Ucount, dpt, dptcount, t2t, t2tw, totw,
                    wetwallcount, tmtw, tmsw, Areqdry, ht, hs, htmt, LMED,
                    tsw_inletdry, tsw_2dry, tsw_2wet, tsw_outwet]
    """
    dp_dew=dew_point(Ftt,fpart,omegai)

    if dp_dew < tis:
        # All dry — delegate to single-phase solver
        Qa=QsolverSP(tit,tis,config,Ftt,Fts,fpart,fpars,mdots,mdott,omegai,Act,Acs,A,SAM,Rfs,Rft,Dto,Dti,Lt,Xt,Jc,Jl,Abas,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc,kappa,Rt,tubetyp,pattern)
        Qguess=Qa[0]; tmtw=Qa[3]; tmsw=Qa[4]; U=Qa[5]; Ucount=Qa[6]; ht=Qa[7]; hs=Qa[8]
        dpt=0.0; dptcount=0; Areqdry=A; htmt=0.0; LMED=0.0
        tos=outlet_temp(Fts,fpars,Qguess,mdots,tis,tit,0,0,config)
        tot=outlet_temp(Ftt,fpart,Qguess,mdott,tit,tis,0,omegai,-1*config)
        t2t=tit; t2tw=dp_dew; totw=tis; omegao=omegai
        return [Qguess,0,U,Ucount,dpt,dptcount,t2t,t2tw,totw,0,tmtw,tmsw,Areqdry,ht,hs,htmt,LMED,0,0,0,0]

    # ── Condensing case ──────────────────────────────────────────────────────
    Gt=mdott/Act; Gs=mdots/Acs
    tot=(tis+tit)/2; totdelta=(tit-tis)/4
    Areq=A*(1-0.01*SAM)+1; count1=0
    Qguess=0; tos=tis; tms=tis; jtot=1.0; Gtcor=Gt; tmtw=tit; tmsw=tis
    ht=0; hs=0; htdry=0; hsdry=0; dpt=0; dptcount=0; Ucount=0
    omegao=omegai; t2t=tit; t2tw=dp_dew; totw=tis
    Areqdry=0; Areqwet=0; htmt=0; LMED=0; QSF=0
    tsw_inletdry=0; tsw_2dry=0; tmtwdry=tit

    while abs(Areq/(A*(1-0.01*SAM))-1)>0.001 and count1<100:
        count1+=1
        dpt=0.001; dptlast=1.1*dpt
        tmtw=(tit+tot)/2+config; count2=0

        # Inner loop: dpt convergence
        while abs(dptlast/dpt-1)>0.001 and count2<100:
            count2+=1; dptlast=dpt
            dp_arr=dPsolver(tit,tot,tmtw,Ftt,fpart,Gt,Dti,Lt,sigmat,omegai,kappa,tubetyp,config)
            dpt=dp_arr[0]; dptcount=dp_arr[2]; omegao=dp_arr[7]
            Qguess=mdott/(1+omegai)*(Cp(Ftt,fpart,tit)*tit+omegai*hgwater(tit)-Cp(Ftt,fpart,tot)*tot-omegao*hgwater(tot))/1000
            tmt=(tit+tot)/2
            tos=outlet_temp(Fts,fpars,Qguess,mdots,tis,tit,0,0,config)
            tms=(tis+tos)/2
            Res=Gs*Dto/max(mu(Fts,fpars,tms),1e-12)
            jtot=Jtotal(Res,Jc,Jl,Abas,Acs,Nss,Ntcc,Ntcw,Nb,Lbe,Lbc)
            Gtcor=Gt*(1+0.5*(omegai+omegao))/(1+omegai)
            tw_arr=tubewall(tms,tmt,Gtcor,Res,Dto,Dti,Xt,Lt,jtot,Rt,Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'wet',pattern)
            tmtw=tw_arr[0]; tmsw=tw_arr[1]; Ucount=tw_arr[3]; hs=tw_arr[5]

        # Find dry/wet boundary t2t
        t2t=tit; t2tdelta=(t2t-tot)/2; dptSF=0.0
        t2tw_guess=dp_dew+1; count3=0; t2s=tos

        while abs(t2tw_guess-dew_point(Ftt,fpart-dptSF/100,omegai))>0.01 and count3<100:
            count3+=1
            if t2t<tit:
                QSF=mdott/(1+omegai)*(Cp(Ftt,fpart,tit)*tit+omegai*hgwater(tit)-Cp(Ftt,fpart,t2t)*t2t-omegai*hgwater(t2t))/1000
                t2s=outlet_temp(Fts,fpars,QSF,mdots,tos,t2t,0,0,-1*config)
                tms_dry=(t2s+tos)/2; tmt_dry=(tit+t2t)/2
                Res_dry=mdots*Dto/(Acs*max(mu(Fts,fpars,tms_dry),1e-12))
                tw2=tubewall(tms_dry,tmt_dry,Gt,Res_dry,Dto,Dti,Xt,Lt,jtot,Rt,Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'dry',pattern)
                tmtwdry=tw2[0]; htdry=tw2[4]; hsdry=tw2[5]; U_dry=tw2[2]
                if abs(tit-tos)>1e-9 and abs(t2t-t2s)>1e-9:
                    LMTD_dry=((tit-tos)-(t2t-t2s))/math.log(max((tit-tos)/(t2t-t2s),1e-9))
                    Areqdry=QSF*1000/max(U_dry*LMTD_dry,1e-9)
                    tsw_inletdry=U_dry/hsdry*(tit-tos)+tos
                    tsw_2dry=U_dry/hsdry*(t2t-t2s)+t2s
                else:
                    Areqdry=0; tsw_inletdry=0; tsw_2dry=0
            else:
                Areqdry=0; t2s=tos; QSF=0; tmtwdry=tit; htdry=0; hsdry=0

            dp_sf=dPsolver(tit,t2t,tmtwdry,Ftt,fpart,Gt,Dti,Lt,sigmat,omegai,kappa,tubetyp,config)
            dptSF=dp_sf[0]*Areqdry/max(A,1e-9)

            tms_wet=(tis+t2s)/2; tmt_wet=(t2t+tot)/2
            Res_wet=mdots*Dto/(Acs*max(mu(Fts,fpars,tms_wet),1e-12))
            tw3=tubewall(tms_wet,tmt_wet,Gtcor,Res_wet,Dto,Dti,Xt,Lt,jtot,Rt,Ftt,Fts,fpart,fpars,Rfs,Rft,kappa,tubetyp,config,'wet',pattern)
            ht=tw3[4]; hs=tw3[5]

            hs_eff=(hs**(-1)+Rfs)**(-1); ht_eff=(ht**(-1)+Dto*Rft/Dti)**(-1)
            ww2=wetwall_temp(Ftt,fpart-dptSF/100,omegai,Rt,hs_eff,ht_eff,t2s,t2t)
            t2tw_guess=ww2[0]
            if abs(t2tw_guess-dew_point(Ftt,fpart-dptSF/100,omegai))>0.01:
                if t2tw_guess>dew_point(Ftt,fpart-dptSF/100,omegai):
                    t2t-=t2tdelta
                else:
                    t2t+=t2tdelta
                t2tdelta/=2

        t2t=min(t2t,tit)
        ww2=wetwall_temp(Ftt,fpart-dptSF/100,omegai,Rt,(hs**(-1)+Rfs)**(-1),(ht**(-1)+Dto*Rft/Dti)**(-1),t2s,t2t)
        t2tw=ww2[0]

        # Enthalpy-based LMED for wet zone
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
        if abs(d1)>1e-9 and abs(d2)>1e-9 and abs(d1/d2)>1e-9:
            LMED=(d1-d2)/math.log(max(d1/d2,1e-9))
        else:
            LMED=max(d1,d2,1e-9)

        htmt=(ht**(-1)+Dto*Rft/Dti)**(-1)/max(Cp(Ftt,fpart,(t2t+tot)/2),1.0)
        Areqwet=(Qguess-QSF)*1000/max(htmt*LMED,1e-9)
        Areq=Areqdry+Areqwet

        if abs(Areq/(A*(1-0.01*SAM))-1)>0.001:
            tot=tot+totdelta if Areq>A*(1-0.01*SAM) else tot-totdelta
            totdelta/=2

    # Final overall quantities
    Qguess=mdott/(1+omegai)*(Cp(Ftt,fpart,tit)*tit+omegai*hgwater(tit)-Cp(Ftt,fpart,tot)*tot-omegao*hgwater(tot))/1000
    dT1=tit-tos; dT2=tot-tis
    if abs(dT1)>1e-9 and abs(dT2)>1e-9 and abs(dT1/dT2)>1e-9:
        LMTD_all=(dT1-dT2)/math.log(max(dT1/dT2,1e-9))
        U=Qguess*1000/max(A*(1-0.01*SAM)*LMTD_all,1e-9)
    else:
        U=0.0
    Areq_safe=max(Areq,1e-9)
    ht=(ht*Areqwet+htdry*Areqdry)/Areq_safe
    hs=(hs*Areqwet+hsdry*Areqdry)/Areq_safe

    return [Qguess,count1,U,Ucount,dpt,dptcount,t2t,t2tw,totw,0,tmtw,tmsw,Areqdry,ht,hs,htmt,LMED,tsw_inletdry,tsw_2dry,ww2[2],wwo[2]]


# ── MODULE 4: GEOMETRY AND UNIT CONVERSIONS ──────────────────────────────────

def tubesheet_thk(typ, dp, t1, t2, t3, t4):
    if typ=='Fixed':
        return t1 if dp==200 else t2
    return t3 if dp==200 else t4

def Nb_custom(Lt, dts1, dts2, dtb, Lbez, Lbc, config):
    Nbmax=int((Lt-dts1-dts2-2*Lbez-dtb)/(Lbc+dtb))+1
    is_odd=(2*int(Nbmax/2)<Nbmax)
    if config=='Odd': return Nbmax if is_odd else Nbmax-1
    return Nbmax-1 if is_odd else Nbmax

def UoMi_flow(uom, value, Ftype, fpar, t, omega):
    """Convert flow input to kg/s. Returns (mdot, type_flag)."""
    u=uom.strip()
    if u=='kg/s':    return value,'m'
    if u=='kg/min':  return value/60,'m'
    if u=='kg/h':    return value/3600,'m'
    if u=='litre/min': return value*rho(Ftype,fpar,t)/60000,'v'
    if u=='m3/s':    return value*rho(Ftype,fpar,t),'v'
    if u=='Am3/s':   return value*rho(Ftype,fpar,t)*(1+omega)/(1+Mw(Ftype)*omega/18.015),'v'
    if u=='m3/h':    return value*rho(Ftype,fpar,t)/3600,'v'
    if u=='Am3/h':   return value*rho(Ftype,fpar,t)/3600*(1+omega)/(1+Mw(Ftype)*omega/18.015),'v'
    if u=='Nm3/h':   return value*rho(Ftype,1.01325,0)/3600,'m'
    if u=='lb/s':    return value/2.205,'m'
    if u=='lb/min':  return value/(2.205*60),'m'
    if u=='lb/h':    return value/(2.205*3600),'m'
    if u=='USgpm':   return value*0.8327*rho(Ftype,fpar,t)/(220*60),'v'
    if u=='Acfm':    return value*rho(Ftype,fpar,t)/(3.281**3*60)*(1+omega)/(1+Mw(Ftype)*omega/18.015),'v'
    if u=='Scfm':    return value*rho(Ftype,1.0138,15.5556)/(3.281**3*60),'m'  # US std: 60°F/14.7psia
    raise ValueError(f'Unknown flow UoM: {uom}')


# ── MODEL GEOMETRY TABLE ──────────────────────────────────────────────────────
# (shell_id, nozzle_id, tube_len, pitch, pattern, rows, otl, nt_miss, first_row,
#  cv_offset, baffle_dia, bcut_cl, nb_fixed, nb_removable, hole_dia, cen_gap_std,
#  ts_thk_200psig_fixed, ts_thk_300psig_fixed, ts_thk_200psig_rem, ts_thk_300psig_rem)
# All dimensions in inches. ts_thk from tubesheet_thk() function.
_MODELS = {
    'W0035': (1.500,0.622,51.125,0.700,'S',2,1.200,0,'hole',0.350,1.438,0.350,28,28,0.516,1.313,1.000,1.000,1000,1000),
    'W0039': (1.500,0.622,59.000,0.700,'S',2,1.200,0,'hole',0.350,1.438,0.350,34,34,0.516,1.313,1.000,1.250,1000,1000),
    'W0045': (2.067,0.622,51.125,0.625,'T',3,1.750,2,'land',0.000,2.000,0.541,28,28,0.516,1.313,1.000,1.000,1000,1000),
    'W0049': (2.067,0.622,59.000,0.625,'T',3,1.750,2,'land',0.000,2.000,0.541,34,34,0.516,1.313,1.000,1.250,1000,1000),
    'W0055': (2.469,0.622,51.125,0.625,'S',3,2.268,0,'hole',0.000,2.375,0.625,28,28,0.516,1.313,1.000,1.000,1000,1000),
    'W0059': (2.469,0.622,59.000,0.625,'S',3,2.477,0,'hole',0.000,2.375,0.625,34,34,0.516,1.313,1.000,1.250,1000,1000),
    'W0065': (3.068,0.824,51.125,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,28,28,0.516,1.313,1.000,1.000,1000,1000),
    'W0069': (3.068,0.824,59.000,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,34,34,0.516,1.313,1.000,1.250,1000,1000),
    'W0070': (3.068,0.824,51.125,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,28,28,0.516,1.313,0.940,0.940,1000,1000),
    'W0090': (3.068,0.824,59.000,0.625,'T',5,2.753,0,'land',0.000,3.000,0.540,34,34,0.516,1.313,0.940,0.940,1000,1000),
    'W0110': (4.026,0.824,51.250,0.625,'RS',7,3.296,0,'land',0.000,3.875,0.875,30,30,0.516,1.313,0.875,0.875,0.875,0.875),
    'W0140': (4.026,0.824,59.000,0.625,'RS',7,3.296,0,'land',0.000,3.875,0.875,36,36,0.516,1.313,0.875,0.875,0.875,0.875),
    'W0160': (5.047,1.049,51.125,0.625,'T',7,3.808,0,'land',0.000,4.875,1.078,28,26,0.516,1.313,1.000,1.000,1000,1000),
    'W0180': (5.047,1.049,59.000,0.625,'T',7,3.808,0,'land',0.000,4.875,1.078,34,34,0.516,1.313,1.000,1.000,1000,1000),
    'W0210': (5.047,1.380,51.250,0.625,'T',7,4.249,0,'land',0.000,4.875,1.082,28,26,0.516,1.313,1.000,1.000,1000,1000),
    'W0230': (5.047,1.380,59.000,0.625,'T',7,4.249,0,'land',0.000,4.875,1.082,34,34,0.516,1.313,1.250,1.250,1000,1000),  # ts_geom=2.3125 design_lbc=1.000 (geometry sheet verified)
    'W0270': (6.065,1.380,51.250,0.625,'T',9,4.875,0,'land',0.000,6.000,1.078,28,28,0.516,1.313,1.063,1.063,1.063,1.063),
    'W0330': (6.065,1.380,59.000,0.625,'T',9,4.875,0,'land',0.000,6.000,1.078,34,34,0.516,1.313,1.063,1.063,1.063,1.063),
    'W0350': (6.065,1.610,51.125,0.625,'T',9,5.500,0,'hole',0.000,6.000,1.078,14,14,0.516,2.625,1.063,1.063,1.063,1.063),
    'W0380': (6.065,1.610,59.000,0.625,'T',9,5.500,0,'hole',0.000,6.000,1.078,18,18,0.516,2.625,1.063,1.063,1.063,1.063),
    'W0420': (7.981,2.067,51.125,0.625,'T',7,7.115,0,'land',0.000,7.875,1.624,14,14,0.516,2.500,1.500,1.500,1.500,1.500),
    'W0490': (7.981,2.067,59.000,0.625,'T',7,7.115,0,'land',0.000,7.875,1.624,18,16,0.516,2.500,1.500,1.500,1.500,1.500),
    'W0650': (10.250,2.469,51.125,0.625,'T',9,9.514,4,'hole',0.000,10.125,2.170,12,12,0.516,2.875,1.500,1.500,1.500,1.500),
    'W0710': (10.250,2.469,59.000,0.625,'T',9,9.514,4,'hole',0.000,10.125,2.170,14,14,0.516,2.875,1.500,1.500,1.500,1.500),
    'W0900': (10.250,2.469,51.125,0.625,'T',13,9.514,2,'hole',0.000,10.125,2.688,12,12,0.516,2.625,1.438,1.438,1.438,1.438),
    'W0980': (10.250,2.469,59.000,0.625,'T',13,9.514,2,'hole',0.000,10.125,2.688,16,16,0.516,2.625,1.438,1.438,1.438,1.438),
    'W1250': (12.090,2.469,51.125,0.687,'T',19,11.492,4,'land',0.000,12.000,2.375,8,8,0.516,4.000,1.563,1.563,1.563,1.563),
    'W1400': (12.090,2.469,59.000,0.687,'T',19,11.492,4,'land',0.000,12.000,2.375,10,10,0.516,4.000,1.563,1.563,1.563,1.563),
    'W1500': (13.250,2.469,51.125,0.625,'T',21,11.952,26,'hole',0.000,13.125,3.188,8,8,0.516,4.000,1.750,1.750,1.750,1.750),
    'W1700': (13.250,2.469,59.000,0.625,'T',21,11.952,26,'hole',0.000,13.125,3.188,10,10,0.516,4.000,1.750,1.750,1.750,1.750),
    'W2000': (13.250,4.026,59.000,0.625,'T',19,12.811,16,'land',0.000,13.125,3.250,8,8,0.516,4.250,1.625,1.625,1.625,1.625),
    'W3000': (17.250,5.047,59.000,0.625,'T',27,15.231,42,'land',0.000,17.000,4.313,8,8,0.516,5.000,2.750,2.750,2.750,2.750),
    'W4000': (19.250,6.065,59.000,0.625,'T',25,18.658,28,'hole',0.000,19.063,5.440,10,10,0.516,3.875,2.563,2.563,2.563,2.563),
    'W5000': (23.250,7.981,59.000,0.625,'T',35,20.137,98,'land',0.000,23.060,5.412,8,8,0.516,3.875,2.250,2.250,2.250,2.250),
}

_DTO = 0.500  # tube OD, inches
_DTI = 0.430  # tube ID, inches
_KAPPA = 1.5e-6  # tube roughness, m (smooth tubes)
_NSS = 0  # seal strip pairs (default)
_DELTA_B = 0.0625  # baffle thickness, inches (from models table AA column)

TUBE_MAT_K = {  # W/m.K
    'Copper (C12200)':339,'Admiralty brass (C44300)':111,'Al brass (C68700)':100,
    '90/10 Cu/Ni (C70600)':45,'70/30 Cu/Ni (C71500)':29.4,
    'Stainless (S3040*)':15.8,'Stainless (S3160*)':15.0,
}
FLUID_CODE = {
    'Air':'g-01','Argon':'g-02','Carbon dioxide':'g-03','Carbon monoxide':'g-04',
    'Helium':'g-05','Hydrogen':'g-06','Methane':'g-07','Nitrogen':'g-08','Oxygen':'g-09',
    'Water':'l-10','Water/ethylene glycol':'l-11','Water/propylene glycol':'l-12','Sea water':'l-13',
}


# Verified geometry overrides (from W1279 geometry sheet)
# Each entry: (ts_geom_in, ts_lbe_in, design_lbc_in)
#   ts_geom   = tubesheet thickness for Lt_eff (heat transfer area)
#   ts_lbe    = tubesheet thickness used in Lbe formula
#   design_lbc = actual Lbc used for Acs/Gs (from geometry sheet F26)
_GEO_OVERRIDES = {
    'W0230': (2.3125, 1.250, 1.000),  # verified: A=20.8ft², Lbe=140mm, Acs=0.001311m²
}

def _build_geometry(model_code, bundle_type, dp_psig):
    """Compute all geometry parameters needed by Qsolver."""
    row = _MODELS.get(model_code)
    if not row: raise ValueError(f'Unknown model: {model_code}')
    (dsi_in,dsn_in,lt_in,pitch_in,pat,n_rows,otl_in,nt_miss,first_row,cv_off_in,
     bdiam_in,bcut_in,nb_f,nb_r,hole_in,lcb_std_in,ts200f,ts300f,ts200r,ts300r)=row

    I=0.0254  # inch→m
    Dsi=dsi_in*I; Dsn=dsn_in*I; Xt=pitch_in*I; OTL=otl_in*I
    Dbaffle=bdiam_in*I; Bcut_cl=bcut_in*I; Dhole=hole_in*I
    Lbc_std=lcb_std_in*I  # standard central gap (column Z, used for Lbe calculation)
    Dto=_DTO*I; Dti=_DTI*I; delta_B=_DELTA_B*I

    # Tubesheet thickness for GEOMETRY (Lt_eff, Lbe)
    # and design Lbc for Acs — use verified overrides where available
    _ovr = _GEO_OVERRIDES.get(model_code)
    if _ovr:
        ts_geom_in, ts_lbe_in, design_lbc_in = _ovr
        Ts = ts_geom_in * I        # used for Lt_eff (heat transfer area)
        Ts_lbe = ts_lbe_in * I     # used for Lbe formula
        Lbc_design = design_lbc_in * I
    else:
        dp=round(dp_psig/100)*100
        if dp not in (200,300): dp=300
        ts_in=tubesheet_thk(bundle_type,dp,ts200f,ts300f,ts200r,ts300r)
        if ts_in>=999: ts_in=ts300f if bundle_type.lower().startswith('f') else ts300r
        Ts=ts_in*I; Ts_lbe=Ts
        Lbc_design=Lbc_std

    # Number of baffles
    Nb=nb_f if bundle_type.lower().startswith('f') else nb_r

    # Row pitch
    if pat=='T':   Xr=Xt*math.sqrt(3)/2
    elif pat=='RS': Xr=Xt/math.sqrt(2)
    else:           Xr=Xt

    # r_ctl: OTL is the outer tube limit DIAMETER; r_ctl = radius to tube centres
    r_ctl=(OTL-Dto)/2

    # Tube count (Cl method, matches spreadsheet)
    y_max=(n_rows/2-0.5)*Xr
    top_has_centre=(first_row=='hole')
    Nt=0
    for idx in range(n_rows):
        yn=y_max-idx*Xr; yn2=yn*yn; rc2=r_ctl**2
        if yn2>rc2: continue
        Cl=math.sqrt(rc2-yn2)-Dto/2
        has_c=top_has_centre if idx%2==0 else (not top_has_centre)
        if Cl<0:
            Nt+=(1 if has_c else 0); continue
        Nteff=int(Cl/Xt)+(0 if has_c else 1)
        Nt+=2*Nteff+(1 if has_c else 0)
    Nt=max(1,Nt-nt_miss)

    Lt_full=lt_in*I                   # full tube length (used in dPsolver — VBA verified)
    Lt_eff=Lt_full-2*Ts               # effective length for heat transfer area

    # Heat transfer area (OD basis)
    A=math.pi*Dto*Lt_eff*Nt

    # Tube-side flow area
    Act=math.pi/4*Dti**2*Nt

    # Tube-side porosity (for KcKe)
    if pat=='T':  A_cell=Xt*Xr
    elif pat=='RS': A_cell=Xt*Xr
    else:          A_cell=Xt**2
    sigmat=math.pi/4*Dti**2/A_cell  # tube free-flow fraction

    # Shell-side crossflow area (Bell-Delaware) — uses design Lbc, not std gap
    A_m_raw=Lbc_design*((Dsi-OTL)+(OTL-Dto)*(1-Dto/Xt))
    Acs=max(A_m_raw*1.31,1e-9)

    # Baffle geometry
    r_shell=Dsi/2
    theta_DS=2*math.acos(max(-1,min(1,Bcut_cl/r_shell)))
    theta_ctl=2*math.acos(max(-1,min(1,Bcut_cl/r_ctl)))
    Fw=(theta_ctl-math.sin(theta_ctl))/(2*math.pi)
    Fc=1-2*Fw
    Ntcc=max(1.0,(OTL-2*Bcut_cl)/Xr)
    Ntcw=0.8*(r_ctl-Bcut_cl)/Xr

    # Clearances
    xi_SB=(Dsi-Dbaffle)/2; xi_BT=(Dhole-Dto)/2

    # Baffle leakage areas
    A_sb=xi_SB*Dsi*(2*math.pi-theta_DS)/2
    A_bt=Nt*math.pi*Dto*xi_BT*(1-Fw)
    A_bas=(Dsi-OTL)*Lbc_std  # bundle-to-shell bypass

    # Bell-Delaware Jc and Jl (pre-computed, passed to Jtotal)
    r_lm=(A_sb+0.5*A_bt)/max(Acs,1e-9)
    r_ss=A_sb/max(A_sb+A_bt,1e-9)
    Jc=0.55+0.72*Fc
    Jl=0.44*(1-r_ss)+(1-0.44*(1-r_ss))*math.exp(-2.6*r_lm)

    # End zone length — VBA: Lbe = (Lt - ts1 - ts2 - Nb*delta_B - (Nb-1)*Lbc_std) / 2
    # Uses Ts_lbe (FB tubesheet) and Lbc_std (standard gap)
    Lbe=max(0.02,(lt_in*I-2*Ts_lbe-Nb*delta_B-(Nb-1)*Lbc_std)/2)

    # Central baffle gap for flow/HTC calculations = design Lbc
    Lbc=Lbc_design

    # Shell nozzle area
    A_csn=max(math.pi/4*Dsn**2,1e-9)

    # End-zone crossflow area
    A_cse=max(A_m_raw*Lbe/max(Lbc,1e-9),1e-9)

    # Wall resistance (K.m²/W, referred to OD)
    # placeholder — will be set from tube material

    return dict(
        Dsi=Dsi,Dsn=Dsn,Lt=Lt_full,Lt_eff=Lt_eff,Xt=Xt,Xr=Xr,pattern=pat,
        N_rows=n_rows,OTL=OTL,Nt_miss=nt_miss,first_row=first_row,
        cv_offset=cv_off_in*I,Dbaffle=Dbaffle,Bcut_cl=Bcut_cl,Nb=Nb,
        Dhole=Dhole,Lbc=Lbc,Lbc_std=Lbc_std,Ts=Ts,delta_B=delta_B,
        Dto=Dto,Dti=Dti,Nt=Nt,A=A,Act=Act,Acs=Acs,
        A_m_raw=A_m_raw,A_sb=A_sb,A_bt=A_bt,A_bas=A_bas,
        A_cse=A_cse,A_csn=A_csn,sigmat=sigmat,
        theta_DS=theta_DS,Fw=Fw,Fc=Fc,Ntcc=Ntcc,Ntcw=Ntcw,
        Jc=Jc,Jl=Jl,Lbe=Lbe,xi_SB=xi_SB,xi_BT=xi_BT,
    )


# ── SHELL-SIDE PRESSURE DROP (Bell-Delaware) ──────────────────────────────────

def _shell_dp_kPa(mdots, T_ms, Fts, fpars, geo, config):
    """Shell-side total pressure drop, kPa."""
    Acs=geo['Acs']; Dsi=geo['Dsi']; Dto=geo['Dto']; Xt=geo['Xt']
    Nb=geo['Nb']; Lbc=geo['Lbc']; Lbe=geo['Lbe']
    Ntcc=geo['Ntcc']; Ntcw=geo['Ntcw']; A_m_raw=geo['A_m_raw']
    A_sb=geo['A_sb']; A_bt=geo['A_bt']; A_bas=geo['A_bas']
    A_cse=geo['A_cse']; A_csn=geo['A_csn']; De=geo.get('De',Dto)
    D_hw=geo.get('D_hw',Dto); theta_DS=geo['theta_DS']
    A_cw=geo.get('A_cw',Acs*0.5)

    Gs=mdots/Acs; rho_s=rho(Fts,fpars,T_ms); mu_s=mu(Fts,fpars,T_ms)
    Re=Gs*Dto/max(mu_s,1e-12)

    fF=f_shell(Re,Dto,Xt,geo['pattern'])
    r_lm=(A_sb+0.5*A_bt)/max(Acs,1e-9)
    Rl=math.exp(-3.3*max(r_lm,1e-9))
    r_bp=A_bas/max(A_m_raw,1e-9)
    Rb=math.exp(-3.7*r_bp)

    dPi=4*fF*Gs**2*Ntcc/(2*rho_s)
    dPx=dPi*Rl*Rb*max(Nb-1,1)

    Gw=mdots/math.sqrt(max(Acs*A_cw,1e-12))
    dPwt=Rl*(2+0.6*Ntcw)*Gw**2/(2*rho_s)
    mu_s_=mu_s; k_=mu_s_  # placeholder
    dPwl=Rl*(26*mu_s*Gw*(Ntcw/max(Dto,1e-9)+Lbc/max(D_hw,1e-9)**2))/rho_s+Gw**2/rho_s
    dPw=(dPwt*Nb if Re>200 else dPwl*Nb if Re<50
         else (dPwt*(Re-50)/150+dPwl*(200-Re)/150)*Nb)

    dPe=dPi*Rl*Rb  # both end zones

    # Nozzle
    sigmaS=A_csn/max(A_cse,1e-9)
    Gn=mdots/max(A_csn,1e-9)
    Kc=(0.5-0.222*sigmaS) if sigmaS<=0.18 else (0.55-0.5*sigmaS)
    Ke=(1-sigmaS)**2
    dPn=(Kc+Ke)*Gn**2/(2*rho_s)

    return (dPx+dPw+dPe+dPn)/1000


# ── MAIN SOLVE FUNCTION ───────────────────────────────────────────────────────

def solve(inputs):
    """
    Main entry point. Accepts flat JSON dict, returns flat JSON dict.
    All calculations use SI units internally; outputs converted to US customary.
    """
    model     = inputs.get('model','W0230')
    btype     = inputs.get('bundle_type','Fixed')
    tube_type = inputs.get('tube_type','Std groove')          # 'Std groove' or 'Plain'
    tube_mat  = inputs.get('tube_material','Stainless (S3040*)')
    tube_fl   = inputs.get('tube_fluid','Air')
    shell_fl  = inputs.get('shell_fluid','Water')

    # Fluid codes
    Ftt = FLUID_CODE.get(tube_fl,'g-01')
    Fts = FLUID_CODE.get(shell_fl,'l-10')

    # Convert inputs to SI
    fpart  = (float(inputs.get('tube_pressure_psig',150))+14.696)/14.5  # bara
    fpart_psia = float(inputs.get('tube_pressure_psig',150))+14.696
    fpars  = 1.01325  # shell side (liquid, pressure irrelevant for properties)
    tit    = (float(inputs.get('tube_temp_in_F',250))-32)/1.8   # °C
    tis    = (float(inputs.get('shell_temp_in_F',70))-32)/1.8   # °C
    Rft    = float(inputs.get('tube_fouling',0))*0.17611         # K.m²/W
    Rfs    = float(inputs.get('shell_fouling',0))*0.17611
    SAM    = float(inputs.get('surface_area_margin',0))
    dp_psig= float(inputs.get('tube_pressure_psig',150))
    glycol_conc = float(inputs.get('glycol_concentration',40))   # % vol for EG/PG

    # Compressor suction
    P_cs_bara = float(inputs.get('suction_pressure_psia',14.7))/14.5
    T_cs_C    = (float(inputs.get('suction_temp_F',85))-32)/1.8
    RH_pct    = float(inputs.get('suction_rh_pct',36))

    # Inlet specific humidity from compressor suction
    Psw_suc = Pswater(T_cs_C)
    Pw_suc  = RH_pct/100*Psw_suc; Pw_suc=min(Pw_suc,P_cs_bara*1e5*0.999)
    omegai  = 18.015/Mw(Ftt)*Pw_suc/max(P_cs_bara*1e5-Pw_suc,1.0)

    # Flow rates
    flow_t  = float(inputs.get('tube_flow',1423))
    uom_t   = inputs.get('tube_flow_uom','Scfm')
    flow_s  = float(inputs.get('shell_flow',60))
    uom_s   = inputs.get('shell_flow_uom','USgpm')

    fpar_shell = glycol_conc if Fts in ('l-11','l-12') else fpars

    mdott,_ = UoMi_flow(uom_t,flow_t,Ftt,fpart,tit,omegai)
    mdots,_ = UoMi_flow(uom_s,flow_s,Fts,fpar_shell,tis,0)

    # Tubetyp for VBA: 'P...' = plain, anything else = grooved
    tubetyp = 'P' if tube_type.lower().startswith('p') else 'G'

    # Wall resistance
    k_tube = TUBE_MAT_K.get(tube_mat,15.8)
    Rt = (0.500*0.0254/2)*math.log(0.500/0.430)/k_tube  # K.m²/W

    # Build geometry
    geo = _build_geometry(model, btype, dp_psig)
    geo['D_hw'] = max(geo.get('Dti',0.010922), geo['A_csn']*4/max(math.pi*geo['Dsn'],1e-9))
    geo['De'] = geo['Dto']
    # Compute A_cw
    A_cw_gross=geo['Dsi']**2/8*(geo['theta_DS']-math.sin(geo['theta_DS']))
    Nt_w=max(1,int(round(geo['Nt']*geo['Fw'])))
    geo['A_cw']=max(1e-9, A_cw_gross-Nt_w*math.pi/4*geo['Dto']**2)

    Dto=geo['Dto']; Dti=geo['Dti']
    Lt=geo['Lt']        # full tube length — passed to Qsolver (dPsolver uses this)
    Lt_eff=geo['Lt_eff'] # effective length — used for heat transfer area only
    Act=geo['Act']; Acs=geo['Acs']; A=geo['A']
    Jc=geo['Jc']; Jl=geo['Jl']; Abas=geo['A_bas']
    Ntcc=geo['Ntcc']; Ntcw=geo['Ntcw']; Nb=geo['Nb']
    Lbe=geo['Lbe']; Lbc=geo['Lbc']; sigmat=geo['sigmat']
    Xt=geo['Xt']; pattern=geo['pattern']

    config = -1  # heat from tubes to shell (aftercooler)

    # Run main solver
    Q_arr=Qsolver(tit,tis,config,Ftt,Fts,fpart,fpar_shell,mdots,mdott,omegai,
                  Act,Acs,A,SAM,Rfs,Rft,Dto,Dti,Lt,sigmat,Xt,
                  Jc,Jl,Abas,_NSS,Ntcc,Ntcw,Nb,Lbe,Lbc,_KAPPA,Rt,tubetyp,pattern)

    Q_kW   = Q_arr[0]  # kW
    U      = Q_arr[2]  # W/m²K effective overall
    dpt_kPa= Q_arr[4]  # kPa
    t2t    = Q_arr[6]  # dry/wet boundary tube temp, °C
    t2tw   = Q_arr[7]  # tube wall temp at dry/wet boundary, °C
    totw   = Q_arr[8]  # tube wall temp at outlet, °C
    tmtw   = Q_arr[10] # mean tube wall temp, °C
    tmsw   = Q_arr[11] # mean shell wall temp, °C
    Areqdry= Q_arr[12] # dry zone area, m²
    ht_avg = Q_arr[13] # average tube-side HTC
    hs_avg = Q_arr[14] # average shell-side HTC
    htmt   = Q_arr[15] # mass transfer coeff / Cp
    LMED   = Q_arr[16]

    # Reconstruct key temperatures
    tot = outlet_temp(Ftt,fpart,Q_kW,mdott,tit,tis,dpt_kPa,omegai,-1*config)
    tos = outlet_temp(Fts,fpar_shell,Q_kW,mdots,tis,tit,0,0,config)

    # Condensate from omegao (dPsolver final omegao)
    dp_final=dPsolver(tit,tot,tmtw,Ftt,fpart,mdott/Act,Dti,Lt,sigmat,omegai,_KAPPA,tubetyp,config)
    omegao=dp_final[7]
    mdotdry=mdott/(1+omegai)
    m_cond=max(0,mdotdry*(omegai-omegao))  # kg/s
    Q_cond=m_cond*2468400  # W (h_fg = 2468.4 kJ/kg, fixed DMI convention)

    # Shell-side pressure drop
    T_ms=(tis+tos)/2
    dps_kPa=_shell_dp_kPa(mdots,T_ms,Fts,fpar_shell,geo,config)

    # Shell-side Re for reporting
    Gs=mdots/Acs; Res=Gs*Dto/max(mu(Fts,fpar_shell,T_ms),1e-12)
    # Tube-side Re
    T_mt=(tit+tot)/2; Ret=mdott/Act*Dti/max(mu(Ftt,fpart,T_mt),1e-12)

    # LMTD (temperature basis for reporting)
    dT1=tit-tos; dT2=tot-tis
    if abs(dT1)>1e-9 and abs(dT2)>1e-9 and abs(dT1/dT2)>1e-9:
        LMTD_temp=(dT1-dT2)/math.log(dT1/dT2)
    else:
        LMTD_temp=abs(dT1+dT2)/2

    # Dew point
    T_dew=dew_point(Ftt,fpart,omegai)

    # Tube wall temps at 4 positions (°C → °F)
    def tw_pos(Tt,Ts):
        if ht_avg>0 and hs_avg>0:
            return (ht_avg*Tt+hs_avg*Ts)/(ht_avg+hs_avg)
        return (Tt+Ts)/2
    wall_temps_F=[
        round(tw_pos(tit,tis)*1.8+32,1),
        round(tw_pos(tit*0.67+tot*0.33,tis*0.67+tos*0.33)*1.8+32,1),
        round(tw_pos(tit*0.33+tot*0.67,tis*0.33+tos*0.67)*1.8+32,1),
        round(tw_pos(tot,tos)*1.8+32,1),
    ]

    # Unit conversions
    def c2f(c): return round(c*1.8+32,1)
    def kw2btu(kw): return round(kw*3412.14,0)
    def wm2k2btu(h): return round(h*0.17611,0)
    def kpa2psi(k): return round(k*0.14504,2)
    def m2ft2(a): return round(a*10.7639,1)

    Q_condensing_pct = round(Q_cond/max(Q_kW*1000,1)*100,1)

    return {
        'Q_Btu_h':           kw2btu(Q_kW),
        'tube_out_F':        c2f(tot),
        'shell_out_F':       c2f(tos),
        'dew_point_F':       c2f(T_dew),
        'dP_tube_psi':       kpa2psi(dpt_kPa),
        'dP_shell_psi':      kpa2psi(dps_kPa),
        'tube_Re':           round(Ret,0),
        'shell_Re':          round(Res,0),
        'tube_HTC_btu':      wm2k2btu(ht_avg),
        'shell_HTC_btu':     wm2k2btu(hs_avg),
        'tube_wall_temps_F': wall_temps_F,
        'area_ft2':          m2ft2(A),
        'surface_area_margin_pct': SAM,
        'overall_U_btu':     wm2k2btu(U),
        'LMTD_R':            round(LMTD_temp*1.8,1),
        'condensing_Btu_h':  kw2btu(Q_cond/1000),
        'condensing_pct':    Q_condensing_pct,
        'condensate_lb_h':   round(m_cond*7936.64,1),
        'Nt':                geo['Nt'],
        't2t_F':             c2f(t2t),
        'LMED':              round(LMED,2),
    }


# ── NETLIFY HANDLER ───────────────────────────────────────────────────────────
_CORS = {
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type',
    'Access-Control-Allow-Methods':'POST, OPTIONS',
}

def handler(event, context):
    if event.get('httpMethod')=='OPTIONS':
        return {'statusCode':200,'headers':_CORS,'body':''}
    try:
        body=json.loads(event.get('body') or '{}')
        result=solve(body)
        return {'statusCode':200,'headers':{**_CORS,'Content-Type':'application/json'},'body':json.dumps(result)}
    except Exception as e:
        import traceback
        return {'statusCode':500,'headers':{**_CORS,'Content-Type':'application/json'},
                'body':json.dumps({'error':str(e),'trace':traceback.format_exc()})}
