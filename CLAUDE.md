# DMI Air Cooled IP Heat Exchanger (DMI-IPAC)

## Project Overview

Web application replacing the W1279 WCAC Excel design tool for Diversified Manufacturing Inc (DMI).

Engineers input compressor and heat exchanger specs, and get a professional performance datasheet PDF output.

**Client:** Charles Cromwell, Diversified Manufacturing Inc
**Contact:** sales@dmimfg.com | (716) 434-5585 | 410 Ohio Street, Lockport NY 14094
**Website:** https://dmimfg.com
**Product line:** IPAC Air Cooled Heat Exchanger / Water Cooled Aftercooler series (models W0035-W5000)

## Tech Stack

- **Phase 1:** Pure static HTML -- single `index.html`, no build step, no backend
- **CSS:** Tailwind CSS via CDN
- **PDF:** jsPDF via CDN
- **JS:** Vanilla JS, no frameworks
- **Deployment:** Netlify free tier (drag & drop `index.html`)
- **Domain (Phase 2):** Porkbun ~$10/yr -- candidates: aircooledip.com, dmipac.com, ipacaircooled.com

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Main web app -- input form + live calc + PDF output |
| `formulas.md` | Engineering formula documentation extracted from W1279 spreadsheet |
| `CLAUDE.md` | This file |

## Spreadsheet Reference (W1279 DMI WCAC Design program I0-1.xlsm)

### Sheets
- **design** -- Main input/output sheet (user-facing design tool)
- **datasheet** -- Formatted output datasheet (customer-facing PDF)
- **calc** -- Thermal performance calculations (iterative solver)
- **geometry** -- Bundle geometry calculations (tube layout by row)
- **models** -- Standard model geometry lookup table (W0035-W5000)
- **menus** -- Fluid property lookup, unit conversion menus
- **notes** -- Interactive validation messages and engineering notes
- **comments** -- Revision history

### Input Fields (from `design` sheet)

**Compressor Details:**
- Suction pressure (psi(a)) -- default 14.7
- Suction temperature (F) -- default 85
- Suction relative humidity (%) -- default 36
- Flow rate at suction (Acfm) -- default 1500
- >1 compression stage (Yes/No)

**Aftercooler Configuration:**
- Base model number (W0035-W5000 dropdown)
- Standard tube length (inches) -- 51" or 59"
- Bundle type (Fixed / Removable)
- Tube side design pressure (psig)
- Tube type (Std groove / Plain)
- Tube material (Copper C12200, Admiralty brass, 90/10 Cu/Ni, 70/30 Cu/Ni, Stainless S3040*, Stainless S3160*)
- Tube length (Standard / Custom)

**Tube Side (compressed gas):**
- Fluid (Air, Argon, CO2, CO, He, H2, CH4 N2, O2)
- Inlet pressure (psig)
- Flow rate (Acfm, Scfm, lb/s, lb/min, lb/h, etc.)
- Inlet temperature (F)
- Fouling resistance (R.ft2.h/Btu)

**Shell Side (cooling water):**
- Fluid (Water, Sea water, Water/ethylene glycol, Water/propylene glycol)
- Inlet flow rate (USgpm, lb/s, lb/min, lb/h, litre/min, m3/s, etc.)
- Inlet temperature (F)
- Fouling resistance (R.ft2.h/Btu)
- Surface area margin (%)

### Output/Calculated Fields

**Tube Side Results:**
- Outlet temperature (F) -- iterative solver
- Pressure loss (psi)
- Reynolds number
- Effective HTC (Btu/h.ft2.R)
- Dew point at inlet (F)

**Shell Side Results:**
- Outlet temperature (F)
- Pressure loss (psi)
- Reynolds number
- Effective HTC (Btu/h.ft2.R)
- Tube surface temperatures (F) at 4 locations

**Overall Performance:**
- Surface area margin (%)
- Surface area fitted (ft2)
- Overall HTC (Btu/h.ft2.R)
- Total heat transfer (Btu/h)
- Condensing heat transfer (Btu/h) + % of total
- Condensate flow (lb/h)
- LMTD (F difference)

### Key Engineering Formulas

**Mass Flow Conversions:**
- Acfm to mass flow: mdot = Q_acfm * rho_actual / 60  (density at actual P,T,humidity)
- Scfm to mass flow: mdot = Q_scfm * rho_dry_60F_14.7psia / 60  (dry gas at 60F, 14.7 psia reference)
- Total mass flow = dry gas + water vapour

**Heat Transfer:**
- Q = mdot * Cp * (T_in - T_out)  -- sensible heat, both sides
- LMTD counterflow: LMTD = (dT1 - dT2) / ln(dT1/dT2)
- Q = U * A * LMTD  -- overall heat transfer
- Overall HTC: 1/U = 1/h_t + Rf_t + R_wall + Rf_s + 1/h_s
- Wall resistance: R_wall = (D_o * ln(D_o/D_i)) / (2 * k_wall)

**Tube-Side HTC (Dittus-Boelter, turbulent, grooved tube data from Wcool 2.03):**
- Re_t = G_t * D_i / mu  where G_t = mdot / A_flow
- Nu = f(Re, Pr, groove_type)  -- curve fit from Wcool for 6850 < Re < 157700
- Variable fluid property correction applied

**Shell-Side HTC (Bell-Delaware / modified Kern):**
- Re_s = G_s * D_e / mu_s
- Crossflow velocity: G_s = mdot_s / A_crossflow
- h_s = j_H * (k_s/D_e) * Re_s * Pr_s^(1/3) * (mu_bulk/mu_wall)^0.14

**Pressure Drop -- Tube Side:**
- dP_f = 4 * f * (L/D_i) * (G_t^2 / (2*rho_mean))
- Entry/exit loss coefficients Kc, Ke from Re
- Iterative: outlet density changes with T_out

**Pressure Drop -- Shell Side (Bell-Delaware):**
- Crossflow dP: dP_cross = f_s * G_s^2 * N_rows / (2*rho_s)
- Window loss (turbulent + laminar terms)
- Nozzle inlet + outlet loss
- Total = crossflow + window + nozzle losses (kPa, convert to psi)

**Condensation:**
- Occurs on tube surface where wall temp < dew point
- Condensate flow: m_cond = Q_latent / h_fg where h_fg = 2468.4 kJ/kg (fixed, DMI convention)
- Q_condensing = m_cond * h_fg

### Standard Model Geometry (from `models` sheet)
Models W0035-W5000. Key parameters per model:
- Shell ID (inches), Shell nozzle ID, Tube length
- Tube spacing, Pattern (T=triangular, S=square, RS=rotated square)
- Number of rows, Max OTL, Number of tubes, 1st row clearance
- Baffle diameter, Baffle cut from CL, Number of baffles
- Tube hole diameter, Central baffle gap, Tubesheet thickness

### Reference Case (from spreadsheet sample data)
- Suction: 14.7 psia, 85F, 36% RH, 1500 Acfm
- Model: W0230, tube length 59", Fixed bundle
- Tube side: Air at 250F, 150 psig, 1423 Scfm
- Shell side: Water at 70F, 60 USgpm
- Expected outputs:
  - Total heat: 292,245 Btu/h
  - Tube outlet: 93.6F (clean), 93.6F (fouled)
  - Shell outlet: 79.8F
  - Tube dP: 9.06 psi | Shell dP: 7.55 psi
  - LMTD: 74.2 R | Overall HTC: 190 Btu/h.ft2.R
  - Surface area: 20.8 ft2
  - Condensate: 39.3 lb/h (14.3% of total heat)

### Fluid Properties Available
**Gases (tube side):** Air, Argon, CO2, CO, He, H2, CH4, N2, O2
**Liquids (shell side):** Water, Sea water (35g/kg), Water/ethylene glycol, Water/propylene glycol

### Tube Materials
- Copper (C12200): k=339 W/m.K
- Admiralty brass (C44300): k=111 W/m.K
- Al brass (C68700): k=100 W/m.K
- 90/10 Cu/Ni (C70600): k=45 W/m.K
- 70/30 Cu/Ni (C71500): k=29.4 W/m.K
- Stainless (S3040*): k=15.8 W/m.K  [code H]
- Stainless (S3160*): k=15 W/m.K

## Deployment

### Phase 1 (Demo)
1. Upload `index.html` to Netlify by drag-and-drop
2. Get instant HTTPS URL to share with Charles at DMI

### Phase 2 (Production)
1. Buy domain at Porkbun (~$10/yr): recommended `aircooledip.com` or `dmipac.com`
2. Connect GitHub repo to Netlify for auto-deploy on push
3. Add custom domain in Netlify dashboard
4. Netlify auto-provisions SSL certificate

## MCP Code Forge Specs
- Spec #1323: Spreadsheet logic extraction -- formulas.md
- Spec #1324: Build demo web app -- index.html
- Spec C (manual): Deploy to Netlify + domain setup guide

## Version History (Spreadsheet)
- I0-0 (2024-10-10): First release
- I0-1 (2025-05-29): Equation corrections, grooved tube pressure loss fix (0.8x correction for Wcool consistency), sea water fluid properties added, shell side tube surface temperatures added, output temperatures rounded to 1dp
