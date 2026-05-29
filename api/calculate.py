"""
DMI IPAC / WCAC Heat Exchanger Calculation Engine
Vercel Serverless Function — server-side only, never served to the browser.

Reference case (W0230, Air 250F/150psig, Water 70F/60USgpm):
  Q = 292,245 Btu/h, tube_out = 93.6F, shell_out = 79.8F,
  dP_tube = 9.06 psi, dP_shell = 7.55 psi, condensate = 39.3 lb/h
"""
from http.server import BaseHTTPRequestHandler
import json, math

# ── Physical constants ────────────────────────────────────────────────────────
TUBE_OD = 0.012700; TUBE_ID = 0.010922; H_FG = 2468.4e3
R_UNIV = 8314.0; M_AIR = 28.97; P_REF = 101325.0; T_REF_K = 288.71

TUBE_MAT_K = {
    'Copper (C12200)': 339.0, 'Admiralty brass (C44300)': 111.0,
    'Al brass (C68700)': 100.0, '90/10 Cu/Ni (C70600)': 45.0,
    '70/30 Cu/Ni (C71500)': 29.4, 'Stainless (S3040*)': 15.8,
    'Stainless (S3160*)': 15.0,
}

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
    (dsi,dsn,lt,pitch,pat,rows,otl,nt_miss,fr,cvo,bdiam,bcut,nb_f,nb_r,hole,lcb,ts) = row
    nb = nb_f if bundle_type.lower().startswith('f') else nb_r
    return dict(Dsi=dsi*i,Dsn=dsn*i,Lt=lt*i,Xt=pitch*i,pattern=pat,N_rows=rows,OTL=otl*i,
                Nt_miss=nt_miss,first_row=fr,cv_offset=cvo*i,Dbaffle=bdiam*i,Bcut_cl=bcut*i,
                Nb=nb,Dhole=hole*i,Lbc=lcb*i,ts_thk=ts*i)

def f_to_c(f): return (f-32.0)/1.8
def c_to_f(c): return c*1.8+32.0
def psig_to_bara(p): return (p+14.696)*0.0689476
def psia_to_bara(p): return p*0.0689476
def kpa_to_psi(k): return k*0.14504
def wm2k_to_btu(h): return h*0.17611

def air_props(T_C, P_bara):
    T=T_C+273.15; rho=P_bara*1e5*M_AIR/(R_UNIV*T)
    mu=1.458e-6*T**1.5/(T+110.4); k=2.495e-3*T**1.5/(T+194.4)
    Cp=1006.0+0.252*T_C-2.62e-4*T_C**2; Pr=mu*Cp/k
    return rho,mu,k,Cp,Pr

_GAS_M={'argon':39.95,'carbon dioxide':44.01,'co2':44.01,'carbon monoxide':28.01,'co':28.01,
        'helium':4.003,'hydrogen':2.016,'methane':16.04,'ch4':16.04,'nitrogen':28.01,'n2':28.01,'oxygen':32.00,'o2':32.00}

def gas_props(fluid, T_C, P_bara):
    if fluid.lower()=='air': return air_props(T_C,P_bara)
    M=_GAS_M.get(fluid.lower(),28.97); T=T_C+273.15
    rho=P_bara*1e5*M/(R_UNIV*T); _,mu,k,Cp,Pr=air_props(T_C,1.0)
    Cp=Cp*28.97/M; ri,*_=air_props(T_C,P_bara); rho=ri*M/28.97
    return rho,mu,k,Cp,Pr

def water_props(T_C):
    T=max(1.0,min(T_C,200.0))
    rho=999.842+6.793e-2*T-9.095e-3*T**2+1.001e-4*T**3-1.120e-6*T**4
    mu=2.414e-5*10**(247.8/(T+133.15)); k=0.5706+1.756e-3*T-6.3e-6*T**2
    Cp=4218.0-3.63*T+0.030*T**2-1.15e-4*T**3; Pr=mu*Cp/k
    return rho,mu,k,Cp,Pr

def liquid_props(fluid, T_C): return water_props(T_C)

_A,_B,_C=16.3872,3885.70,230.170

def specific_humidity_from_rh(rh_pct, T_C, P_bara):
    Ps=math.exp(_A-_B/(T_C+_C))/100.0; Pw=min(rh_pct/100.0*Ps,P_bara*0.999)
    return 0.622*Pw/(P_bara-Pw)

def dew_point_C(omega, P_bara):
    Pw=omega*P_bara*100.0/(omega+0.622)
    return -100.0 if Pw<=0 else _B/(_A-math.log(Pw))-_C

def gas_flow_to_kgs(value, uom, fluid, P_bara, T_C, omega):
    u=uom.strip().lower()
    if u=='acfm': rho,*_=gas_props(fluid,T_C,P_bara); return value*rho/60.0/35.3147
    if u=='scfm': rho_r=P_REF*M_AIR/(R_UNIV*T_REF_K); return value*rho_r/60.0/35.3147*(1.0+omega)
    if u=='lb/s': return value*0.453592
    if u=='lb/min': return value*0.453592/60.0
    if u=='lb/h': return value*0.453592/3600.0
    if u=='kg/s': return value
    if u=='kg/min': return value/60.0
    if u=='kg/h': return value/3600.0
    if u in('am³/s','am3/s'): rho,*_=gas_props(fluid,T_C,P_bara); return value*rho
    if u in('am³/h','am3/h'): rho,*_=gas_props(fluid,T_C,P_bara); return value*rho/3600.0
    if u=='nm³/h': return value*P_REF*M_AIR/(R_UNIV*273.15)/3600.0
    raise ValueError(f'Unknown gas flow UoM: {uom}')

def liquid_flow_to_kgs(value, uom, fluid, T_C):
    rho,*_=liquid_props(fluid,T_C); u=uom.strip().lower()
    if u=='usgpm': return value*6.30902e-5*rho
    if u=='lb/s': return value*0.453592
    if u=='lb/min': return value*0.453592/60.0
    if u=='lb/h': return value*0.453592/3600.0
    if u in('litre/min','l/min'): return value*rho/60000.0
    if u in('m³/s','m3/s'): return value*rho
    if u in('m³/h','m3/h'): return value*rho/3600.0
    if u=='kg/s': return value
    if u=='kg/min': return value/60.0
    if u=='kg/h': return value/3600.0
    raise ValueError(f'Unknown liquid flow UoM: {uom}')

def bundle_geometry(g):
    Do=TUBE_OD; Di=TUBE_ID
    Dsi=g['Dsi']; Dsn=g['Dsn']; Lt=g['Lt']; Xt=g['Xt']; pat=g['pattern']
    N_rows=g['N_rows']; OTL=g['OTL']; Nt_miss=g['Nt_miss']; Dbaffle=g['Dbaffle']
    Bcut_cl=g['Bcut_cl']; Nb=g['Nb']; Dhole=g['Dhole']; Lbc=g['Lbc']
    ts_thk=g['ts_thk']; cv_off=g['cv_offset']; first_row=g['first_row']
    Xr=Xt*math.sqrt(3.0)/2.0 if pat=='T' else (Xt/math.sqrt(2.0) if pat=='RS' else Xt)
    r_ctl=(OTL-Do)/2.0; y_max=(N_rows/2.0-0.5)*Xr
    top_has_centre=(first_row=='hole'); Nt=0
    for idx in range(N_rows):
        yn=y_max-idx*Xr; yn2=yn*yn; rc2=r_ctl*r_ctl
        if yn2>rc2: continue
        Cl=math.sqrt(rc2-yn2)-Do/2.0
        has_c=top_has_centre if idx%2==0 else (not top_has_centre)
        if Cl<0: Nt+=(1 if has_c else 0); continue
        Nteff=int(Cl/Xt)+(0 if has_c else 1)
        Nt+=2*Nteff+(1 if has_c else 0)
    Nt=max(1,Nt-Nt_miss); Lt_eff=Lt-2.0*ts_thk; A=math.pi*Do*Lt_eff*Nt
    Act=math.pi/4.0*Di**2*Nt
    De=(4.0*(Xt**2*math.sqrt(3.0)/4.0-math.pi*Do**2/8.0)/(math.pi*Do/2.0) if pat in('T','RS')
        else 4.0*(Xt**2-math.pi*Do**2/4.0)/(math.pi*Do)); De=max(De,Do*0.1)
    A_m_raw=Lbc*((Dsi-OTL)+(OTL-Do)*(1.0-Do/Xt)); Acs=max(A_m_raw*1.31,1e-6)
    r_shell=Dsi/2.0; theta_DS=2.0*math.acos(max(-1.0,min(1.0,Bcut_cl/r_shell)))
    theta_ctl=2.0*math.acos(max(-1.0,min(1.0,Bcut_cl/r_ctl)))
    Fw=(theta_ctl-math.sin(theta_ctl))/(2.0*math.pi); Fc=1.0-2.0*Fw
    Ntcc=max(1.0,(OTL-2.0*Bcut_cl)/Xr); Ntcw=0.8*(r_ctl-Bcut_cl)/Xr
    xi_SB=(Dsi-Dbaffle)/2.0; xi_BT=(Dhole-Do)/2.0
    A_sb=xi_SB*Dsi*(2.0*math.pi-theta_DS)/2.0
    A_bt=Nt*math.pi*Do*xi_BT*(1.0-Fw)
    A_bas_raw=(Dsi-OTL)*Lbc; A_bas=A_bas_raw
    A_cw_gross=Dsi**2/8.0*(theta_DS-math.sin(theta_DS))
    Nt_w=max(1,int(round(Nt*Fw))); A_cw=max(1e-6,A_cw_gross-Nt_w*math.pi/4.0*Do**2)
    delta_B_lbe=0.00772; Lbe=max(0.02,(Lt_eff-Nb*delta_B_lbe-(Nb-1)*Lbc)/2.0)
    A_cse=max(A_m_raw*Lbe/max(Lbc,1e-9),1e-6); A_csn=max(math.pi/4.0*Dsn**2,1e-6)
    sigmaS=A_csn/max(A_cse,1e-9)
    perim_w=math.pi*Do*Nt_w+Dsi*theta_DS/2.0; D_hw=max(De,4.0*A_cw/max(perim_w,1e-9))
    return dict(**g,Nt=Nt,Xr=Xr,De=De,Lt_eff=Lt_eff,A=A,Act=Act,Acs=Acs,A_m_raw=A_m_raw,
                A_cw=A_cw,A_sb=A_sb,A_bt=A_bt,A_bas=A_bas,A_cse=A_cse,A_csn=A_csn,
                sigmaS=sigmaS,D_hw=D_hw,Fw=Fw,Fc=Fc,Ntcc=Ntcc,Ntcw=Ntcw,theta_DS=theta_DS,
                Lbe=Lbe,xi_SB=xi_SB,xi_BT=xi_BT)

def bd_corrections(geo, Re_s):
    Fw=geo['Fw']; Fc=geo['Fc']; Nb=geo['Nb']; Ntcc=geo['Ntcc']; Lbc=geo['Lbc']; Lbe=geo['Lbe']
    Acs=geo['Acs']; A_m_raw=geo['A_m_raw']; A_sb=geo['A_sb']; A_bt=geo['A_bt']; A_bas=geo['A_bas']
    Jc=0.55+0.72*Fc
    r_lm=(A_sb+0.5*A_bt)/max(Acs,1e-9); r_ss=A_sb/max(A_sb+A_bt,1e-9)
    Jl=0.44*(1.0-r_ss)+(1.0-0.44*(1.0-r_ss))*math.exp(-2.6*r_lm)
    r_bp=A_bas/max(A_m_raw,1e-9); C_bp=1.25 if Re_s>=100 else 1.35
    Jb=math.exp(-C_bp*r_bp) if 0<Ntcc else 1.0
    Jr=1.0; x=Lbe/max(Lbc,1e-9)
    Js=Nb/((Nb-1)+x) if Nb>1 else 1.0
    return Jc,Jl,Jb,Jr,Js

def tube_htc(mdot,T_C,P_bara,fluid,Rf_K,geo,tube_type='Std groove'):
    Gt=mdot/geo['Act']; rho,mu,k,Cp,Pr=gas_props(fluid,T_C,P_bara)
    Re=max(Gt*TUBE_ID/max(mu,1e-10),100.0)
    Nu=(0.0519*Re**0.8*max(Pr,0.1)**(1.0/3.0) if 'groove' in tube_type.lower()
        else 0.023*Re**0.8*max(Pr,0.1)**0.4)
    h_t=Nu*k/TUBE_ID; return 1.0/(1.0/h_t+Rf_K),Re

def shell_htc(mdot,T_C,fluid,Rf_K,geo):
    Gs=mdot/geo['Acs']; rho,mu,k,Cp,Pr=liquid_props(fluid,T_C)
    Re=max(Gs*TUBE_OD/max(mu,1e-10),1.0)
    h_s0=0.385*(k/TUBE_OD)*Re**0.6*max(Pr,0.1)**(1.0/3.0)
    Jc,Jl,Jb,Jr,Js=bd_corrections(geo,Re)
    h_s=h_s0*Jc*Jl*Jb*Jr*Js; return 1.0/(1.0/h_s+Rf_K),Re,Jc,Jl,Jb,Jr,Js

def tube_dp_kPa(mdot,Tit_C,Tot_C,P_bara,fluid,geo,tube_type='Std groove'):
    Gt=mdot/geo['Act']; ri,mi,*_=gas_props(fluid,Tit_C,P_bara); ro,mo,*_=gas_props(fluid,Tot_C,P_bara)
    Re=Gt*TUBE_ID/max((mi+mo)/2.0,1e-10)
    if 'groove' in tube_type.lower():
        dP=0.80*4.0*1.2006*max(Re,1.0)**(-0.25)*(geo['Lt_eff']/TUBE_ID)*Gt**2/(2.0*ro)
    else:
        f=0.316*max(Re,1)**(-0.25) if Re>=2300 else 64.0/max(Re,1)
        dP=f*(geo['Lt_eff']/TUBE_ID)*Gt**2/(2.0*(ri+ro)/2.0)
    return dP/1000.0

def shell_dp_kPa(mdot,T_C,fluid,geo):
    Acs=geo['Acs']; Nb=geo['Nb']; Lbc=geo['Lbc']; Lbe=geo['Lbe']
    Ntcc=geo['Ntcc']; Ntcw=geo['Ntcw']; A_cw=geo['A_cw']
    A_sb=geo['A_sb']; A_bt=geo['A_bt']; A_bas=geo['A_bas']; A_m_raw=geo['A_m_raw']
    A_cse=geo['A_cse']; A_csn=geo['A_csn']; sigmaS=geo['sigmaS']; D_hw=geo['D_hw']
    De=geo['De']; Gs=mdot/Acs; rho,mu,k,Cp,Pr=liquid_props(fluid,T_C)
    Re=Gs*TUBE_OD/max(mu,1e-10); fF=0.855*max(Re,1.0)**(-0.20)
    r_lm=(A_sb+0.5*A_bt)/max(Acs,1e-9); Rl=math.exp(-3.3*max(r_lm,1e-9))
    r_bp=A_bas/max(A_m_raw,1e-9); Rb=math.exp(-3.7*r_bp)
    dPi=4.0*fF*Gs**2*Ntcc/(2.0*rho); dPx=dPi*Rl*Rb*max(Nb-1,1)
    Gw=mdot/math.sqrt(max(Acs*A_cw,1e-12))
    dPwt=Rl*(2.0+0.6*Ntcw)*Gw**2/(2.0*rho)
    dPwl=Rl*(26.0*mu*Gw*(Ntcw/De+Lbc/D_hw**2))/rho+Gw**2/rho
    dPw=(dPwt*Nb if Re>200 else dPwl*Nb if Re<50
         else (dPwt*(Re-50)/150.0+dPwl*(200-Re)/150.0)*Nb)
    dPe=dPi*Rl*Rb
    Gn=mdot/max(A_csn,1e-9); Kc=(0.5-0.222*sigmaS if sigmaS<=0.18 else 0.55-0.5*sigmaS)
    Ke=(1.0-sigmaS)**2; dPn=(Kc+Ke)*Gn**2/(2.0*rho)
    return (dPx+dPw+dPe+dPn)/1000.0

def solve(inputs):
    model=inputs.get('model','W0230'); btype=inputs.get('bundle_type','Fixed')
    ttype=inputs.get('tube_type','Std groove'); tmat=inputs.get('tube_material','Stainless (S3040*)')
    k_tube=TUBE_MAT_K.get(tmat,15.8); fluid_t=inputs.get('tube_fluid','Air'); fluid_s=inputs.get('shell_fluid','Water')
    P_t=psig_to_bara(float(inputs.get('tube_pressure_psig',150))); T_it=f_to_c(float(inputs.get('tube_temp_in_F',250)))
    flow_t=float(inputs.get('tube_flow',1423)); uom_t=inputs.get('tube_flow_uom','Scfm')
    Rf_t=float(inputs.get('tube_fouling',0))*0.17611; T_is=f_to_c(float(inputs.get('shell_temp_in_F',70)))
    flow_s=float(inputs.get('shell_flow',60)); uom_s=inputs.get('shell_flow_uom','USgpm')
    Rf_s=float(inputs.get('shell_fouling',0))*0.17611; SAM=float(inputs.get('surface_area_margin',0))
    P_cs=psia_to_bara(float(inputs.get('suction_pressure_psia',14.7)))
    omega=specific_humidity_from_rh(float(inputs.get('suction_rh_pct',36)),f_to_c(float(inputs.get('suction_temp_F',85))),P_cs)
    T_dew=dew_point_C(omega,P_t)
    mdot_t=gas_flow_to_kgs(flow_t,uom_t,fluid_t,P_t,T_it,omega)
    mdot_s=liquid_flow_to_kgs(flow_s,uom_s,fluid_s,T_is); mdot_dry=mdot_t/(1.0+omega)
    geo=bundle_geometry(model_geometry(model,btype))
    A_eff=geo['A']/(1.0+SAM/100.0); R_w=(TUBE_OD/2.0)*math.log(TUBE_OD/TUBE_ID)/k_tube

    def _eval(T_ot_try):
        T_mt=(T_it+T_ot_try)/2.0; _,_,_,Cp_t,_=gas_props(fluid_t,T_mt,P_t)
        Q_s=mdot_t*Cp_t*(T_it-T_ot_try)
        Tw=(1594.0*T_ot_try+3400.0*T_is)/4994.0
        oo=(min(omega,specific_humidity_from_rh(100,T_ot_try,P_t)) if T_dew>T_is and Tw<T_dew and omega>0 else omega)
        Qt=Q_s+max(0,mdot_dry*(omega-oo))*H_FG
        _,_,_,Cs1,_=liquid_props(fluid_s,T_is); Tos=T_is+Qt/max(mdot_s*Cs1,1e-9)
        _,_,_,Cs2,_=liquid_props(fluid_s,(T_is+Tos)/2.0); Tos=T_is+Qt/max(mdot_s*Cs2,1e-9)
        Tms=(T_is+Tos)/2.0; dT1=T_it-Tos; dT2=T_ot_try-T_is
        if dT1<1e-6 or dT2<1e-6: return Qt,Tos,Tms,1e-6,None,None
        LMTD=(dT1-dT2)/math.log(max(dT1/dT2,1e-9))
        ht,_=tube_htc(mdot_t,T_mt,P_t,fluid_t,Rf_t,geo,ttype)
        hs,_,_,_,_,_,_=shell_htc(mdot_s,Tms,fluid_s,Rf_s,geo)
        U=1.0/(1.0/hs+Rf_s+R_w+Rf_t+1.0/ht)
        Tw2=(ht*T_ot_try+hs*T_is)/max(ht+hs,1.0)
        if T_dew>T_is and Tw2<T_dew and omega>0:
            oo2=min(omega,specific_humidity_from_rh(100,T_ot_try,P_t))
            U=U*(1.0+0.08*min(1.0,(omega-oo2)/omega))
        return Qt,Tos,Tms,LMTD,U,Qt-U*A_eff*LMTD

    T_lo,T_hi=T_is+0.5,T_it-0.5
    for _ in range(60):
        T_mid=(T_lo+T_hi)/2.0; *_,res=_eval(T_mid)
        if res is None or res>0: T_lo=T_mid
        else: T_hi=T_mid
        if T_hi-T_lo<5e-5: break
    T_ot=(T_lo+T_hi)/2.0
    Q_req,T_os,T_ms,LMTD,U,_=_eval(T_ot)
    ht,Re_t=tube_htc(mdot_t,(T_it+T_ot)/2,P_t,fluid_t,Rf_t,geo,ttype)
    hs,Re_s,Jc,Jl,Jb,Jr,Js=shell_htc(mdot_s,T_ms,fluid_s,Rf_s,geo)
    T_wo=(ht*T_ot+hs*T_is)/max(ht+hs,1.0)
    oo_out=(min(omega,specific_humidity_from_rh(100,T_ot,P_t)) if T_dew>T_is and T_wo<T_dew and omega>0 else omega)
    mc=max(0,mdot_dry*(omega-oo_out)); Qc=mc*H_FG
    dPt=tube_dp_kPa(mdot_t,T_it,T_ot,P_t,fluid_t,geo,ttype); dPs=shell_dp_kPa(mdot_s,T_ms,fluid_s,geo)
    def tw(Tt,Ts): return (ht*Tt+hs*Ts)/max(ht+hs,1.0)
    wt=[round(c_to_f(tw(T_it,T_is)),1),round(c_to_f(tw(T_it*.67+T_ot*.33,T_is*.67+T_os*.33)),1),
        round(c_to_f(tw(T_it*.33+T_ot*.67,T_is*.33+T_os*.67)),1),round(c_to_f(tw(T_ot,T_os)),1)]
    return {
        'Q_Btu_h':round(Q_req*3.41214,0),'tube_out_F':round(c_to_f(T_ot),1),
        'shell_out_F':round(c_to_f(T_os),1),'dew_point_F':round(c_to_f(T_dew),1),
        'dP_tube_psi':round(kpa_to_psi(dPt),2),'dP_shell_psi':round(kpa_to_psi(dPs),2),
        'tube_Re':round(Re_t,0),'shell_Re':round(Re_s,0),
        'tube_HTC_btu':round(wm2k_to_btu(ht),0),'shell_HTC_btu':round(wm2k_to_btu(hs),0),
        'tube_wall_temps_F':wt,'area_ft2':round(geo['A']*10.7639,1),
        'surface_area_margin_pct':SAM,'overall_U_btu':round(wm2k_to_btu(U),0),
        'LMTD_R':round(LMTD*1.8,1),'condensing_Btu_h':round(Qc*3.41214,0),
        'condensing_pct':round(Qc/max(Q_req,1)*100,1),'condensate_lb_h':round(mc*7936.64,1),
        'Nt':geo['Nt'],
    }

# ── Vercel serverless handler ─────────────────────────────────────────────────
_CORS_HEADERS = [
    ('Content-Type', 'application/json'),
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Headers', 'Content-Type'),
    ('Access-Control-Allow-Methods', 'POST, OPTIONS'),
]

class handler(BaseHTTPRequestHandler):
    def _send(self, status, body_bytes):
        self.send_response(status)
        for k, v in _CORS_HEADERS:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_OPTIONS(self):
        self._send(200, b'')

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            result = solve(json.loads(body))
            self._send(200, json.dumps(result).encode())
        except Exception as exc:
            import traceback
            self._send(500, json.dumps({'error': str(exc), 'trace': traceback.format_exc()}).encode())

    def log_message(self, *args):
        pass   # silence Vercel access logs
