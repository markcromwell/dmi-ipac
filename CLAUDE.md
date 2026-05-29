# DMI Air Cooled IP Heat Exchanger (DMI-IPAC)

## Project Overview

Web application replacing the W1279 WCAC Excel design tool for Diversified Manufacturing Inc (DMI).

Engineers input compressor and heat exchanger specs, and get a professional performance datasheet PDF output.

**Client:** Charles Cromwell, Diversified Manufacturing Inc
**Contact:** sales@dmimfg.com | (716) 434-5585 | 410 Ohio Street, Lockport NY 14094
**Website:** https://dmimfg.com
**Product line:** IPAC Air Cooled Heat Exchanger / Water Cooled Aftercooler series (models W0035-W5000)

## Architecture

The engineering calculation logic (Bell-Delaware shell-side method, grooved tube HTC curve-fit
from Wcool 2.03, iterative solver) is **proprietary IP** and must never be exposed in
client-readable code (JS, HTML source).

**Architecture: static frontend + Netlify Functions backend**

```
Browser (index.html)
    │  JSON POST  { inputs }
    ▼
Netlify Function  (netlify/functions/calculate.py)   ← hidden from users
    │  JSON response  { results }
    ▼
Browser renders results + PDF download
```

### Frontend (`index.html`)
- Static HTML, Tailwind CSS (CDN), vanilla JS
- Collects inputs, POSTs to `/.netlify/functions/calculate`
- Renders results table and datasheet PDF (jsPDF CDN)
- No calculation logic in the browser

### Backend (`netlify/functions/calculate.py`)
- Python 3.x Netlify Function
- Implements: fluid properties, mass flow conversions, geometry, Bell-Delaware HTC,
  Dittus-Boelter tube HTC, iterative solver, pressure drops, condensation
- Returns all output fields as JSON
- Source never served to the browser

### Deployment
- **Netlify free tier** — connect GitHub repo, auto-deploy on push
- Function executes in ~0.5s per design point (well within 10s limit)
- No database, no auth, no sessions — one-shot calculator

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Frontend form + results display + PDF output |
| `netlify/functions/calculate.py` | Calculation engine (proprietary, server-side only) |
| `netlify.toml` | Netlify build config |
| `formulas.md` | Engineering formula reference (internal, not served) |
| `CLAUDE.md` | This file |

## Spreadsheet Reference (W1279 DMI WCAC Design program I0-1.xlsm)

Original program dates to ~1975, ported through successive platforms into this Excel workbook.
Current revision I0-1 (2025-05-29).

### Sheets
- **design** — Main input/output sheet (user-facing design tool)
- **datasheet** — Formatted output datasheet (customer-facing PDF)
- **calc** — Thermal performance calculations (iterative VBA solver)
- **geometry** — Bundle geometry calculations (tube layout by row)
- **models** — Standard model geometry lookup table (W0035-W5000)
- **menus** — Fluid property lookup, unit conversion menus
- **notes** — Interactive validation messages and engineering notes
- **comments** — Revision history

### Input Fields

**Compressor Details:**
- Suction pressure (psi(a)) — default 14.7
- Suction temperature (F) — default 85
- Suction relative humidity (%) — default 36
- Flow rate at suction (Acfm) — default 1500
- >1 compression stage (Yes/No)

**Aftercooler Configuration:**
- Base model number (W0035-W5000 dropdown)
- Bundle type (Fixed / Removable)
- Tube type (Std groove / Plain)
- Tube material (Copper C12200, Admiralty brass, 90/10 Cu/Ni, 70/30 Cu/Ni, Stainless S3040*, Stainless S3160*)
- Tube length (Standard / Custom)

**Tube Side (compressed gas):**
- Fluid (Air, Argon, CO2, CO, He, H2, CH4, N2, O2)
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

### Output Fields

**Tube Side:** Outlet temp (F), Pressure loss (psi), Reynolds number, Effective HTC (Btu/h.ft2.R), Dew point at inlet (F)

**Shell Side:** Outlet temp (F), Pressure loss (psi), Reynolds number, Effective HTC (Btu/h.ft2.R), Tube surface temperatures (F) at 4 locations

**Overall:** Surface area margin (%), Surface area fitted (ft2), Overall HTC (Btu/h.ft2.R), Total heat transfer (Btu/h), Condensing heat (Btu/h + % total), Condensate flow (lb/h), LMTD (F)

## Reference Case (for validating the calculation engine)

| Input | Value |
|-------|-------|
| Suction | 14.7 psia, 85°F, 36% RH, 1500 Acfm |
| Model | W0230, Fixed bundle |
| Tube side | Air, 150 psig, 1423 Scfm, 250°F, no fouling |
| Shell side | Water, 70°F, 60 USgpm, no fouling |

| Expected Output | Value |
|----------------|-------|
| Total heat transfer | 292,245 Btu/h |
| Tube outlet temp | 93.6°F (clean = fouled, no fouling) |
| Shell outlet temp | 79.8°F |
| Tube pressure loss | 9.06 psi |
| Shell pressure loss | 7.55 psi |
| LMTD | 74.2°R |
| Overall HTC | 190 Btu/h.ft2.R |
| Surface area | 20.8 ft2 |
| Condensate flow | 39.3 lb/h |
| Condensing heat | 41,711 Btu/h (14.3% of total) |

**If the calculation engine produces different numbers for this case, something is wrong.**

## Engineering Reference

See `formulas.md` for complete formula documentation:
- Unit conversions (pressure, temperature, flow, HTC, fouling)
- Humidity and dew point (Antoine equation)
- Standard model geometry table (all W0035-W5000 with all columns)
- Bundle geometry calculations (tube count, flow areas, clearances)
- Tube-side HTC (Dittus-Boelter + Wcool grooved tube fit)
- Shell-side HTC (Bell-Delaware: ideal bundle + 5 correction factors Jc, Jl, Jb, Jr, Js)
- Tube-side pressure drop (friction + entry/exit losses, iterative)
- Shell-side pressure drop (crossflow + window + end zone + nozzle losses)
- Condensation model (dew point, condensate flow, h_fg = 2468.4 kJ/kg)
- Iterative solver description
- Verified reference case intermediate values (SI)

## Tube Dimensions (fixed for all models)
- OD: 0.500" = 0.01270 m
- Wall: 0.035" = 0.000889 m
- ID: 0.430" = 0.010922 m

## Tube Materials
- Copper (C12200): k=339 W/m.K
- Admiralty brass (C44300): k=111 W/m.K
- Al brass (C68700): k=100 W/m.K
- 90/10 Cu/Ni (C70600): k=45 W/m.K
- 70/30 Cu/Ni (C71500): k=29.4 W/m.K
- Stainless (S3040*): k=15.8 W/m.K [code H]
- Stainless (S3160*): k=15.0 W/m.K

## Latent Heat
h_fg = 2468.4 kJ/kg (fixed DMI convention, per Wcool 2.03 consistency)

## Deployment

### Phase 1 (Demo)
1. Connect GitHub repo to Netlify
2. Netlify auto-builds and deploys on push
3. Share HTTPS URL with Charles at DMI

### Phase 2 (Production)
1. Buy domain at Porkbun (~$10/yr): recommended `aircooledip.com` or `dmipac.com`
2. Add custom domain in Netlify dashboard
3. Netlify auto-provisions SSL certificate

## Local Development

### Full stack (frontend + API)
```
netlify dev
```
Starts frontend at http://localhost:8888 and API at http://localhost:8888/.netlify/functions/calculate

### Unit tests (no server needed, fast, run in CI)
```
python -m pytest netlify/functions/tests/test_calculate_unit.py -v
```
Tests the calculation engine directly — no HTTP. Should pass in <1s.

### Integration tests (start netlify dev first)
```
python -m pytest netlify/functions/tests/test_calculate_api.py -v
```
Automatically skipped if server isn't running — CI never breaks.

### Reference case for manual validation

Enter these inputs and check the outputs match:

**Inputs:** Model W0230 · Fixed · Std Groove · Stainless S304*  
Compressor: 14.7 psia / 85°F / 36% RH · Air side: 150 psig / 1423 Scfm / 250°F  
Water side: 70°F / 60 USgpm

**Expected outputs:**

| Output | Value | Tolerance |
|--------|-------|-----------|
| Total heat | 292,245 Btu/h | ±5,000 |
| Tube outlet | 93.6°F | ±3°F* |
| Shell outlet | 79.8°F | ±0.5°F |
| Tube dP | 9.06 psi | ±0.5 |
| Shell dP | 7.55 psi | ±0.5 |
| Condensate | 39.3 lb/h | ±2.0 |
| Surface area | 20.8 ft² | ±0.5 |

*Tube outlet tolerance is wider because the spreadsheet VBA uses a two-zone wet/dry
condensation model (formulas.md §12.2) which our simplified single-zone implementation
approximates. All other values are within 1-2% of the spreadsheet.

## MCP Code Forge Specs
- Spec #1323: Spreadsheet logic extraction → formulas.md (COMPLETED manually 2026-05-29)
- Spec #1324: Build web app (frontend + Netlify Function backend)

## Spreadsheet Version History
- I0-0 (2024-10-10): First release
- I0-1 (2025-05-29): Equation corrections, grooved tube pressure loss fix (0.8x correction
  for Wcool consistency), sea water fluid properties added, shell side tube surface
  temperatures added, output temperatures rounded to 1dp
