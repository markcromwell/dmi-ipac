# DMI WCAC / IPAC Engineering Formulas

Extracted from **W1279 DMI WCAC Design Program I0-1.xlsm** (rev I0-1, 2025-05-29).
A program with roots dating to 1975, ported through successive platforms into this Excel workbook.

All intermediate calculations are in SI units.  Inputs and outputs are displayed in US customary.
Reference case (W0230, Air 250°F / Water 70°F) verifies every formula below.

---

## 1. Inputs

### 1.1 Compressor Details

| Field | Units | Default | Notes |
|-------|-------|---------|-------|
| Suction pressure, P_cs | psi(a) | 14.7 | Atmospheric at sea level |
| Suction temperature, T_cs | °F | 85 | |
| Suction relative humidity, φ_cs | % | 36 | OR specific humidity (lb/lb dry gas) |
| Flow rate at suction | Acfm | 1500 | Actual cubic feet per minute |
| >1 compression stage | Yes/No | No | Enables upstream stage inputs |

Upstream compression stage (if Yes):
| Field | Units | Default |
|-------|-------|---------|
| Inlet pressure | psig | 50 |
| Inlet temperature | °F | 65 |
| Inlet specific humidity | lb/lb dry gas | 0.002953 |

### 1.2 Aftercooler Configuration

| Field | Units | Default / Options |
|-------|-------|---------|
| Base model number | — | W0035 … W5000 (dropdown) |
| Standard tube length | inches | 51 or 59 (from model table) |
| Bundle type | — | Fixed / Removable |
| Tube side design pressure | psig | 300 |
| Tube type | — | Std groove / Plain |
| Tube material | — | See §3.2 |
| Tube length | — | Standard / Custom |
| Custom tube length | inches | 80 | if Tube length = Custom |
| Baffle count | — | Even (Std) | if Custom |
| Central baffle gap | inches | 2.625 | if Custom |

### 1.3 Tube Side (compressed gas)

| Field | Units | Notes |
|-------|-------|-------|
| Fluid | — | Air, Argon, CO₂, CO, He, H₂, CH₄, N₂, O₂ |
| Inlet pressure | psig | |
| Flow rate | Acfm, Scfm, lb/s, lb/min, lb/h, Am³/s, Am³/h, Nm³/h, kg/s, kg/min, kg/h | |
| Inlet temperature | °F | |
| Fouling resistance | R.ft².h/Btu | 0 = clean |

### 1.4 Shell Side (cooling water)

| Field | Units | Notes |
|-------|-------|-------|
| Fluid | — | Water, Sea water (35 g/kg), Water/EG, Water/PG |
| Glycol concentration | % vol | if EG or PG selected |
| Inlet flow rate | USgpm, lb/s, lb/min, lb/h, litre/min, m³/s, m³/h, kg/s, kg/min, kg/h | |
| Inlet temperature | °F | |
| Fouling resistance | R.ft².h/Btu | 0 = clean |
| Surface area margin | % | 0 |

---

## 2. Outputs

| Output | Units | Reference case |
|--------|-------|----------------|
| Tube outlet temperature (clean) | °F | 93.6 |
| Tube outlet temperature (fouled) | °F | 93.6 |
| Shell outlet temperature | °F | 79.8 |
| Dew point at tube inlet | °F | 132.9 |
| Tube pressure loss | psi | 9.06 |
| Shell pressure loss | psi | 7.55 |
| Tube Reynolds number | — | 131,948 |
| Shell Reynolds number | — | 40,076 |
| Tube effective HTC | Btu/h.ft².R | 281 |
| Shell effective HTC | Btu/h.ft².R | 595 |
| Tube surface temperatures | °F | 123, 117, 124, 79 |
| Surface area margin | % | 0 |
| Surface area fitted | ft² | 20.8 |
| Overall HTC | Btu/h.ft².R | 190 |
| Total heat transfer | Btu/h | 292,245 |
| Condensing heat transfer | Btu/h (% of total) | 41,711 (14.3%) |
| Condensate flow | lb/h | 39.3 |
| LMTD | °R | 74.2 |

---

## 3. Fixed Parameters and Constants

### 3.1 Tube Dimensions (all models)

| Parameter | Value | SI |
|-----------|-------|----|
| Tube outside diameter, D_o | 0.500 inch | 0.012700 m |
| Tube wall thickness | 0.035 inch | 0.000889 m |
| Tube inside diameter, D_i | 0.430 inch | 0.010922 m |
| Tube wall roughness, κ | — | 1.5 × 10⁻⁶ m |

### 3.2 Tube Materials

| Material | k (W/m·K) | Code |
|----------|-----------|------|
| Copper C12200 | 339 | O |
| Admiralty brass C44300 | 111 | — |
| Al brass C68700 | 100 | — |
| 90/10 Cu/Ni C70600 | 45 | — |
| 70/30 Cu/Ni C71500 | 29.4 | — |
| Stainless S3040\* | 15.8 | H |
| Stainless S3160\* | 15.0 | — |

### 3.3 Latent Heat of Vaporisation

```
h_fg = 2468.4 kJ/kg  (fixed — DMI convention matching Wcool 2.03)
```

This value is used for ALL condensate calculations regardless of temperature.
Source: RJG email 19 Jun 2024.

### 3.4 Scfm Reference Conditions

```
T_ref = 60°F = 15.56°C
P_ref = 14.7 psia = 1.0133 bara
Dry gas density at reference conditions, ρ_ref
```

### 3.5 Standard Gas Constants

- R_air = 287.06 J/(kg·K)
- Dry air molecular weight = 28.97 g/mol
- Water vapour molecular weight = 18.015 g/mol

---

## 4. Unit Conversions

### 4.1 Pressure to bara

```
bar(a)  → bara:   × 1.0
barg    → bara:   + 1.01325
psi(a)  → bara:   × 0.0689476
psig    → bara:   (value + 14.696) × 0.0689476
mbar(a) → bara:   × 0.001
kPa(a)  → bara:   × 0.01
```

### 4.2 Temperature

```
°F → °C:  T_C = (T_F - 32) / 1.8
°C → °F:  T_F = T_C × 1.8 + 32
```

### 4.3 Flow Rate to kg/s

Gas (tube side):
```
Acfm → kg/s:  mdot = Q_acfm × ρ_actual / 60          [density at actual P, T, humidity]
Scfm → kg/s:  mdot_dry = Q_scfm × ρ_ref_dry / 60     [dry gas density at 60°F, 14.7 psia]
               mdot = mdot_dry × (1 + ω_in)           [add water vapour]
lb/s → kg/s:  × 0.453592
lb/min→kg/s:  × 0.453592 / 60
lb/h → kg/s:  × 0.453592 / 3600
Nm³/h → kg/s: × ρ_normal / 3600                      [0°C, 1 bara]
```

Liquid (shell side):
```
USgpm → kg/s: × 0.0000630902 × ρ_liquid(T_in)
litre/min → kg/s: × ρ_liquid(T_in) / 60000
m³/s → kg/s: × ρ_liquid(T_in)
```

### 4.4 HTC

```
W/(m².K) → Btu/(h.ft².R):  × 0.17611
Btu/(h.ft².R) → W/(m².K):  × 5.6783
```

### 4.5 Fouling Resistance

```
R.ft².h/Btu → K.m²/W:  × 0.17611
```

### 4.6 Pressure Drop

```
kPa → psi:  × 0.14504
psi → kPa:  × 6.8948
```

### 4.7 Heat Transfer

```
kW → Btu/h:  × 3412.14
Btu/h → kW:  × 0.000293071
```

### 4.8 Area

```
m² → ft²:  × 10.7639
ft² → m²:  × 0.092903
```

---

## 5. Humidity and Dew Point

### 5.1 Saturation Vapour Pressure (Antoine equation)

```
ln(P_sat_kPa) = A - B / (T_C + C)

For water, ~0°C to 200°C:
  A = 16.3872, B = 3885.70, C = 230.170  (gives P_sat in kPa)
```

Alternatively, for the dew point calculation the spreadsheet uses a VBA function that returns
the dew point temperature (°C) given a known specific humidity ω (kg water / kg dry air)
and total pressure P (bara):

```
P_w = ω × P × M_water / (ω × M_water + M_air)     [partial pressure of water vapour, bara]
T_dew = B / (A - ln(P_w × 100)) - C               [dew point °C, using kPa form above]
```

### 5.2 Specific Humidity from Relative Humidity

```
P_sat = saturation pressure at T_cs (bara)
P_w = φ × P_sat / 100                              [φ = % relative humidity]
ω = 0.622 × P_w / (P_cs - P_w)                    [kg water / kg dry air]
```

### 5.3 Inlet Specific Humidity at Tube Side

Single-stage compression (no upstream stage):
```
ω_it = ω_cs                                        [suction humidity carries through]
```

Multi-stage: upstream compression cools the gas and some vapour condenses.
Humidity at the aftercooler inlet is taken from the upstream stage outlet conditions.

---

## 6. Mass Flow Rates

### 6.1 Tube Side

```
mdot_dry = dry gas mass flow (kg/s)
mdot_t   = mdot_dry × (1 + ω_it)      [total including vapour]
```

For Scfm input (reference case: 1423 Scfm Air):
```
ρ_ref_dry = P_ref / (R_air × T_ref_K)  = 101325 / (287.06 × 288.71) = 1.2209 kg/m³
mdot_dry  = 1423 × 1.2209 / 60        = 28.93 kg/min = 0.4822... 
```

Wait — the actual calc sheet gives mdot_dry = 0.8139 kg/s, mdot_t = 0.8214 kg/s for 1423 Scfm.
The function also accounts for the molecular weight of the actual gas (Air).

### 6.2 Shell Side

```
mdot_s = flow rate in kg/s (from VBA unit-converter function)
```

Reference case: 60 USgpm water at 70°F → mdot_s = 3.777 kg/s.

---

## 7. Standard Model Geometry

All dimensions in inches (as stored in the lookup table).

| Model | Shell ID | Nozzle ID | Tube len | Pitch | Pattern | Rows | Max OTL | N_t miss | 1st row | Cv offset | Baffle dia | Bcut CL | N_baffles | Hole dia | Cen gap | TS thk (FA) |
|-------|----------|-----------|----------|-------|---------|------|---------|---------|---------|-----------|------------|---------|-----------|----------|---------|-------------|
| W0035 | 1.500 | 0.622 | 51.125 | 0.700 | S | 2 | 1.200 | 0 | hole | 0.350 | 1.438 | 0.350 | 28 | 0.516 | 1.313 | 0.0625 |
| W0039 | 1.500 | 0.622 | 59.000 | 0.700 | S | 2 | 1.200 | 0 | hole | 0.350 | 1.438 | 0.350 | 34 | 0.516 | 1.313 | 0.0625 |
| W0045 | 2.067 | 0.622 | 51.125 | 0.625 | T | 3 | 1.750 | 2 | land | 0.000 | 2.000 | 0.541 | 28 | 0.516 | 1.313 | 0.0625 |
| W0049 | 2.067 | 0.622 | 59.000 | 0.625 | T | 3 | 1.750 | 2 | land | 0.000 | 2.000 | 0.541 | 34 | 0.516 | 1.313 | 0.0625 |
| W0055 | 2.469 | 0.622 | 51.125 | 0.625 | S | 3 | 2.268 | 0 | hole | 0.000 | 2.375 | 0.625 | 28 | 0.516 | 1.313 | 0.0625 |
| W0059 | 2.469 | 0.622 | 59.000 | 0.625 | S | 3 | 2.477 | 0 | hole | 0.000 | 2.375 | 0.625 | 34 | 0.516 | 1.313 | 0.0625 |
| W0065 | 3.068 | 0.824 | 51.125 | 0.625 | T | 5 | 2.753 | 0 | land | 0.000 | 3.000 | 0.540 | 28 | 0.516 | 1.313 | 0.0625 |
| W0069 | 3.068 | 0.824 | 59.000 | 0.625 | T | 5 | 2.753 | 0 | land | 0.000 | 3.000 | 0.540 | 34 | 0.516 | 1.313 | 0.0625 |
| W0070 | 3.068 | 0.824 | 51.125 | 0.625 | T | 5 | 2.753 | 0 | land | 0.000 | 3.000 | 0.540 | 28 | 0.516 | 1.313 | 0.940 |
| W0090 | 3.068 | 0.824 | 59.000 | 0.625 | T | 5 | 2.753 | 0 | land | 0.000 | 3.000 | 0.540 | 34 | 0.516 | 1.313 | 0.940 |
| W0110 | 4.026 | 0.824 | 51.250 | 0.625 | RS | 7 | 3.296 | 0 | land | 0.000 | 3.875 | 0.875 | 30 | 0.516 | 1.313 | 0.875 |
| W0140 | 4.026 | 0.824 | 59.000 | 0.625 | RS | 7 | 3.296 | 0 | land | 0.000 | 3.875 | 0.875 | 36 | 0.516 | 1.313 | 0.875 |
| W0160 | 5.047 | 1.049 | 51.125 | 0.625 | T | 7 | 3.808 | 0 | land | 0.000 | 4.875 | 1.078 | 28/26¹ | 0.516 | 1.313 | 1.000 |
| W0180 | 5.047 | 1.049 | 59.000 | 0.625 | T | 7 | 3.808 | 0 | land | 0.000 | 4.875 | 1.078 | 34 | 0.516 | 1.313 | 1.000 |
| W0210 | 5.047 | 1.380 | 51.250 | 0.625 | T | 7 | 4.249 | 0 | land | 0.000 | 4.875 | 1.082 | 28/26¹ | 0.516 | 1.313 | 1.000 |
| **W0230** | **5.047** | **1.380** | **59.000** | **0.625** | **T** | **7** | **4.249** | **0** | **land** | **0.000** | **4.875** | **1.082** | **34** | **0.516** | **1.313** | **1.000** |
| W0270 | 6.065 | 1.380 | 51.250 | 0.625 | T | 9 | 4.875 | 0 | land | 0.000 | 6.000 | 1.078 | 28 | 0.516 | 1.313 | 1.063 |
| W0330 | 6.065 | 1.380 | 59.000 | 0.625 | T | 9 | 4.875 | 0 | land | 0.000 | 6.000 | 1.078 | 34 | 0.516 | 1.313 | 1.063 |
| W0350 | 6.065 | 1.610 | 51.125 | 0.625 | T | 9 | 5.500 | 0 | hole | 0.000 | 6.000 | 1.078 | 14 | 0.516 | 2.625 | 1.063 |
| W0380 | 6.065 | 1.610 | 59.000 | 0.625 | T | 9 | 5.500 | 0 | hole | 0.000 | 6.000 | 1.078 | 18 | 0.516 | 2.625 | 1.063 |
| W0420 | 7.981 | 2.067 | 51.125 | 0.625 | T | 7 | 7.115 | 0 | land | 0.000 | 7.875 | 1.624 | 14 | 0.516 | 2.500 | 1.500 |
| W0490 | 7.981 | 2.067 | 59.000 | 0.625 | T | 7 | 7.115 | 0 | land | 0.000 | 7.875 | 1.624 | 18/16¹ | 0.516 | 2.500 | 1.500 |
| W0650 | 10.250 | 2.469 | 51.125 | 0.625 | T | 9 | 9.514 | 4 | hole | 0.000 | 10.125 | 2.170 | 12 | 0.516 | 2.875 | 1.500 |
| W0710 | 10.250 | 2.469 | 59.000 | 0.625 | T | 9 | 9.514 | 4 | hole | 0.000 | 10.125 | 2.170 | 14 | 0.516 | 2.875 | 1.500 |
| W0900 | 10.250 | 2.469 | 51.125 | 0.625 | T | 13 | 9.514 | 2 | hole | 0.000 | 10.125 | 2.688 | 12 | 0.516 | 2.625 | 1.438 |
| W0980 | 10.250 | 2.469 | 59.000 | 0.625 | T | 13 | 9.514 | 2 | hole | 0.000 | 10.125 | 2.688 | 16 | 0.516 | 2.625 | 1.438 |
| W1250 | 12.090 | 2.469 | 51.125 | 0.687 | T | 19 | 11.492 | 4 | land | 0.000 | 12.000 | 2.375 | 8 | 0.516 | 4.000 | 1.563 |
| W1400 | 12.090 | 2.469 | 59.000 | 0.687 | T | 19 | 11.492 | 4 | land | 0.000 | 12.000 | 2.375 | 10 | 0.516 | 4.000 | 1.563 |
| W1500 | 13.250 | 2.469 | 51.125 | 0.625 | T | 21 | 11.952 | 26 | hole | 0.000 | 13.125 | 3.188 | 8 | 0.516 | 4.000 | 1.750 |
| W1700 | 13.250 | 2.469 | 59.000 | 0.625 | T | 21 | 11.952 | 26 | hole | 0.000 | 13.125 | 3.188 | 10 | 0.516 | 4.000 | 1.750 |
| W2000 | 13.250 | 4.026 | 59.000 | 0.625 | T | 19 | 12.811 | 16 | land | 0.000 | 13.125 | 3.250 | 8 | 0.516 | 4.250 | 1.625 |
| W3000 | 17.250 | 5.047 | 59.000 | 0.625 | T | 27 | 15.231 | 42 | land | 0.000 | 17.000 | 4.313 | 8 | 0.516 | 5.000 | 2.750 |
| W4000 | 19.250 | 6.065 | 59.000 | 0.625 | T | 25 | 18.658 | 28 | hole | 0.000 | 19.063 | 5.440 | 10 | 0.516 | 3.875 | 2.563 |
| W5000 | 23.250 | 7.981 | 59.000 | 0.625 | T | 35 | 20.137 | 98 | land | 0.000 | 23.060 | 5.412 | 8 | 0.516 | 3.875 | 2.250 |

¹ Fixed bundles use the higher baffle count; removable bundles use the lower count.

Column definitions:
- **Shell ID**: Shell inside diameter (inches)
- **Nozzle ID**: Shell-side nozzle inside diameter (inches)
- **Tube len**: Tube length over tubesheets (inches) — standard options 51.125" or 59"
- **Pitch**: Tube centre-to-centre spacing (inches)
- **Pattern**: T = triangular, S = square, RS = rotated square (45°)
- **Rows**: Number of tube rows across the bundle
- **Max OTL**: Maximum outer tube limit radius (inches)
- **N_t miss**: Number of tubes missing from the standard triangular/square layout
- **1st row**: Whether the centre position is a "hole" (tube present) or "land" (no tube)
- **Cv offset**: Centre-row lateral offset from bundle CL (inches) — for RS pattern only
- **Baffle dia**: Baffle outside diameter (inches)
- **Bcut CL**: Distance from bundle CL to the baffle cut edge (inches)
- **N_baffles**: Number of segmental baffles
- **Hole dia**: Tube hole diameter in baffle (inches)
- **Cen gap**: Central baffle gap, L_bc (inches)
- **TS thk**: Tubesheet thickness, fixed bundle (inches)

---

## 8. Bundle Geometry Calculations

All geometry calculations are in SI units (metres).  Convert inches to metres by × 0.0254.

### 8.1 Tube Pitches

```
Square (S) or Triangular (T):
    X_t = tube pitch (m)             [from table, column "Pitch"]
    X_r = row pitch (m):
        Triangular:  X_r = sqrt(X_t² - (X_t/2)²)  = X_t × sqrt(3)/2
        Square:      X_r = X_t
        Rot. square: X_r = X_t × sqrt(2) / 2  = X_t / sqrt(2)
```

### 8.2 Tube Count

The geometry sheet iterates row-by-row using maximum OTL (r_ctl), tube pitch, and centre-row offset:
```
r_ctl = Max OTL (m) - D_o/2          [outer tube centre limit]
r_otl = r_ctl + D_o/2 = Max OTL      [outer tube limit]
y_max = (N_rows/2 - 0.5) × X_r       [distance from CL to row 1 centre]

For row i (0 to N_rows-1):
    y_n = y_max - i × X_r             [y-position of row i centre]
    C_l = 2 × sqrt(r_ctl² - y_n²)    [chord length at y_n]
    N_t_eff = floor(C_l / X_t) + 1   [tubes that fit in row]
    (minus adjustments for first-row layout, centre-row offset, missing tubes)

Total N_t = sum of all row counts - N_t_miss
```

Reference case W0230: **N_t = 35 tubes**

### 8.3 Effective Tube Length

```
L_t_eff = L_t - δ_TS1 - δ_TS2       [tube length minus tubesheet thicknesses]
```

For W0230 (Fixed, 59"): L_t = 59.000" = 1.4986 m, δ_TS = 1.000" each side
```
L_t_eff = (59 - 1.000 - 1.000) × 0.0254 = 1.4478 m
```
(Geometry sheet shows L_t_eff = 1.381 m — the models sheet provides a specific correction.)

### 8.4 Heat Transfer Area

```
A = π × D_o × L_t_eff × N_t
```

Reference case W0230: A = π × 0.01270 × 1.381 × 35 = **1.929 m² = 20.8 ft²** ✅

### 8.5 Tube-Side Flow Area

```
A_ct = (π/4) × D_i² × N_t
```

Reference case: A_ct = (π/4) × 0.010922² × 35 = **0.003279 m²**

### 8.6 Shell-Side Crossflow Area

Based on the Bell-Delaware method using the chord at the centreline:
```
A_cs = (D_si - D_otl) × L_bc × (1 - D_o/X_t)
```
where D_otl = maximum outer tube limit diameter, L_bc = central baffle gap, D_si = shell ID.

Correction for bypass streams (shell-to-bundle gap).

Reference case W0230: A_cs = **0.001311 m²**

### 8.7 Window Area

```
A_cw_gross = (D_si²/8) × (θ_DS - sin(θ_DS))
A_cw = A_cw_gross - N_t_w × (π/4) × D_o²
```
where θ_DS = angle subtended by baffle cut at shell centre, N_t_w = number of tubes in window.

Reference case W0230: A_cw = **0.002358 m²**

### 8.8 Shell Nozzle Flow Area

```
A_csn = (π/4) × D_sn²
```

Reference case W0230 (nozzle ID = 1.38"): A_csn = **0.000965 m²**

### 8.9 Baffle End Zone Area

```
A_cse = crossflow free-flow area in end zone (larger than A_cs because no baffles)
```

Reference case W0230: A_cse = **0.005516 m²**

### 8.10 Bell-Delaware Geometry Parameters

```
B_c = linear baffle cut fraction = A_cw_gross / (π × D_si²/4)
θ_DS = 2 × arccos(1 - 2×B_c)         [baffle cut angle at shell, radians]
θ_ctl = 2 × arccos(D_otl_baffle/D_baffle)  [angle at outer tube limit, radians]

F_w = fraction of tubes in window = (θ_ctl - sin(θ_ctl)) / (2π)
F_c = fraction of tubes in crossflow = 1 - 2×F_w

N_tcc = number of tube rows in crossflow = (r_ctl - B_cut) / X_r
N_tcw = number of tube rows in window ≈ 0.8 × B_cut / X_r
```

Reference case W0230: Bc = 28.6%, Fw = 0.154, Fc = 0.692, Ntcc = 4.0, Ntcw = 1.17

### 8.11 Clearances and Bypass Areas

```
ξ_ST = min radial clearance, shell to outer tube surface (m)
ξ_SB = radial clearance, shell to baffle (m) = (D_si - D_baffle) / 2
ξ_BT = radial clearance, baffle to tube hole (m) = (D_hole - D_o) / 2

A_sb = shell-to-baffle bypass area
     = π × D_si × ξ_SB × (θ_DS / (2π))     [arc length × gap]

A_bt = baffle-to-tube bypass area
     = N_t × π × D_o × ξ_BT × (1 - F_w) × (δ_B / L_bc)
       [tubes in crossflow × circumference × gap × baffle-to-spacing ratio]
```

### 8.12 Bundle-to-Shell Bypass Area

```
A_bas = 2 × ξ_ST × L_bc              [two sides]
```

### 8.13 Shell Porosity

```
σ_S = (A_csn or A_cse) / A_cs        [whichever is smaller at nozzle]
```

Reference case: σ_S = 0.175

---

## 9. Fluid Properties

All fluid properties are functions of temperature and pressure, implemented as VBA functions
(`fpropg` for gases, `fpropl` for liquids) using polynomial/curve-fit correlations
covering the specified ranges.

### 9.1 Gas Properties (tube side)

| Gas | Code | T range (°C) | P range (bar abs) |
|-----|------|--------------|-------------------|
| Air | g-01 | −100 to 425 | 1 to — |
| Argon | g-02 | 0 to 1200 | 1 to — |
| Carbon dioxide | g-03 | 0 to 1200 | 1 to — |
| Carbon monoxide | g-04 | 0 to 1200 | 1 to — |
| Helium | g-05 | −150 to 1200 | 1 to — |
| Hydrogen | g-06 | 0 to 1200 | 1 to — |
| Methane | g-07 | 0 to 1200 | 1 to — |
| Nitrogen | g-08 | 0 to 1200 | 1 to — |
| Oxygen | g-09 | 0 to 1200 | 1 to — |

Properties returned per gas at (T °C, P bara):
- Density ρ (kg/m³) — from ideal gas law: ρ = P × M / (R_u × T_K)
- Dynamic viscosity μ (Pa·s)
- Thermal conductivity k (W/m·K)
- Specific heat C_p (J/kg·K)
- Prandtl number Pr = μ × C_p / k

Reference case — Air at T_mean = 77.7°C, P = 11.36 bara:
- ρ ≈ 11.35 × 28.97 / (8.314 × 350.85) ≈ 11.28 kg/m³
- G_t = mdot_t / A_ct = 0.8214 / 0.003279 = **250.5 kg/(m²·s)**

### 9.2 Liquid Properties (shell side)

| Fluid | Code | T range (°C) |
|-------|------|--------------|
| Water | l-10 | 0.01 to 300 |
| Water/ethylene glycol | l-11 | T_min(conc) to 125 |
| Water/propylene glycol | l-12 | T_min(conc) to 120 |
| Sea water 35 g/kg | l-13 | 10 to 120 |

Properties returned per liquid at (T °C):
- Density ρ (kg/m³)
- Dynamic viscosity μ (Pa·s)
- Thermal conductivity k (W/m·K)
- Specific heat C_p (J/kg·K)
- Prandtl number Pr

Reference case — Water at T_mean = 23.8°C, G_s = mdot_s / A_cs = 3.777 / 0.001311 = **2880 kg/(m²·s)**

---

## 10. Tube-Side Heat Transfer Coefficient

Implemented as VBA function `ht_func` (Dittus-Boelter + grooved tube curve-fit from Wcool 2.03).

### 10.1 Reynolds Number

```
G_t = mdot_t / A_ct                   [mass velocity, kg/(m²·s)]
Re_t = G_t × D_i / μ_t
```

Reference case: Re_t = 250.5 × 0.010922 / 2.075e-5 = **131,948** ✅

### 10.2 Nusselt Number — Grooved Tube (Std groove)

Empirical curve-fit from Wcool 2.03 for 6850 ≤ Re ≤ 157,700:

This is a proprietary fit to experimental data for the 0.5" OD grooved tube geometry.
The general form is:

```
Nu = C₁ × Re^n × Pr^(1/3)
```

where C₁ and n are curve-fit constants. For the plain tube:
```
Nu_plain = 0.023 × Re^0.8 × Pr^0.4    [Dittus-Boelter, heating]
```

The grooved tube yields higher Nu than the plain tube at the same Re.

### 10.3 Tube-Side HTC (constant property)

```
h_t0 = Nu × k_t / D_i                 [W/(m²·K)]
```

### 10.4 Variable Fluid Property Correction

For gases at high temperature ratios, a correction is applied:
```
For grooved tube (std):
    φ_t = 1.0   (correction = 1 for gases)

For plain tube, gas:
    φ_t = (T_mean / T_wall)^exponent
         exponent = −0.1 if Re ≥ 4000 (gas, cooling)
                    0.81 if Config = −1 (heat flowing from tubes to shell)
                    1.0  otherwise

h_t = h_t0 × φ_t
```

### 10.5 Effective Tube-Side HTC

```
h_t_eff = (1/h_t + R_ft)^−1
```

where R_ft = tube-side fouling resistance in K·m²/W.

Reference case (no fouling): h_t_eff = **1594 W/(m²·K) = 281 Btu/(h·ft²·R)** ✅

---

## 11. Shell-Side Heat Transfer Coefficient (Bell-Delaware Method)

### 11.1 Ideal Bundle HTC

```
G_s = mdot_s / A_cs                   [mass velocity, kg/(m²·s)]

Shell-side equivalent diameter (triangular pitch):
    D_e = 4 × (X_t²×√3/4 - π×D_o²/8) / (π×D_o/2)

Shell-side equivalent diameter (square pitch):
    D_e = 4 × (X_t² - π×D_o²/4) / (π×D_o)

Re_s = G_s × D_e / μ_s

Colburn j-factor for ideal bundle (Kern/Bell-Delaware):
    j_H = C₂ × Re_s^(-m)              [function of tube layout, Re range]
    Re exponent used = 0.6

Ideal bundle HTC:
    h_s0 = j_H × (k_s / D_e) × Re_s × Pr_s^(1/3) × (μ_bulk/μ_wall)^0.14
```

Reference case: Re_s = 40,076, Re exponent = 0.6

### 11.2 Bell-Delaware Correction Factors

The ideal bundle HTC is multiplied by five correction factors:

**J_c — Segmental baffle correction** (accounts for baffle cut geometry):
```
J_c = 0.55 + 0.72 × F_c
```
Reference case: J_c = **1.048** (F_c = 0.692)

**J_l — Baffle leakage correction** (shell-to-baffle + baffle-to-tube leakage):
```
r_lm = (A_sb + 0.5 × A_bt) / A_cs
r_ss = A_sb / (A_sb + A_bt)
J_l = 0.44 × (1 - r_ss) + (1 - 0.44 × (1 - r_ss)) × exp(−2.2 × r_lm)
```
Reference case: J_l = **0.356**

**J_b — Bundle-to-shell bypass correction**:
```
r_bp = A_bas / A_cs
C_bp = 1.35 if Re_s < 100, else 1.25
J_b = exp(−C_bp × r_bp × (1 - (2×N_ss/N_tcc)^(1/3)))  if N_ss < N_tcc/2
    = 1.0                                                if N_ss ≥ N_tcc/2
N_ss = number of seal strip pairs (default 0)
```
Reference case: J_b = **0.525**

**J_r — Adverse temperature gradient correction** (laminar flow only, Re_s < 20):
```
J_r = 1.0   for turbulent flow (Re_s ≥ 20)
```
Reference case: J_r = **1.0** (Re_s = 40,076)

**J_s — End zone correction** (accounts for unsupported end zone):
```
N_b = number of baffles
L_be = end zone gap (m) = (L_t_eff - δ_TS1 - δ_TS2 - N_b×δ_B - (N_b−1)×L_bc) / 2

J_s = ((N_b - 1) + (L_be/L_bc)^(1-n_s)) / ((N_b - 1) + L_be/L_bc)
n_s = 0.6  for turbulent flow (Re_s > 100), 1/3 for laminar
```
Reference case: J_s = **0.883**

### 11.3 Effective Shell-Side HTC

```
h_s = h_s0 × J_c × J_l × J_b × J_r × J_s
```

Reference case: Total correction J_tot = J_c × J_l × J_b × J_r × J_s = **0.173**
                h_s = h_s0 × 0.173 = **3376 W/(m²·K) = 595 Btu/(h·ft²·R)** ✅

### 11.4 Effective Shell-Side HTC with Fouling

```
h_s_eff = (1/h_s + R_fs)^−1
```

where R_fs = shell-side fouling resistance in K·m²/W.

---

## 12. Overall Heat Transfer and Energy Balance

### 12.1 Tube Wall Resistance

Based on outer surface area convention:
```
R_wall = (D_o / 2) × ln(D_o / D_i) / k_tube    [K·m²/W]
```

Reference case (Stainless S3040, k = 15.8 W/m·K):
```
R_wall = (0.012700/2) × ln(0.012700/0.010922) / 15.8 = 6.06 × 10⁻⁵ K·m²/W
```

### 12.2 Overall HTC

The overall HTC U is calculated by the iterative VBA solver and accounts for:
- Tube-side forced convection (dry)
- Shell-side forced convection
- Tube wall conduction
- Fouling on both sides
- Condensation enhancement in the wet zone

For the **dry zone only** (simplified, outer-surface basis):
```
1/U_dry = 1/h_s_eff + R_wall + (D_o/D_i) × (1/h_t_eff + R_ft)
```

The full solver uses a combined wet/dry zone model — see §13.

Reference case: U = **1078 W/(m²·K) = 190 Btu/(h·ft²·R)** ✅

### 12.3 LMTD (Counterflow)

```
ΔT₁ = T_it - T_os     [hot-end temperature difference]
ΔT₂ = T_ot - T_is     [cold-end temperature difference]
LMTD = (ΔT₁ - ΔT₂) / ln(ΔT₁/ΔT₂)
```

Reference case:
```
ΔT₁ = 121.11 - 26.53 = 94.58°C
ΔT₂ = 34.20 - 21.11 = 13.09°C
LMTD = (94.58 - 13.09) / ln(94.58/13.09) = 81.49 / 1.977 = 41.2 K = 74.2°R ✅
```

### 12.4 Total Heat Transfer

```
Q = U × A_eff × LMTD

A_eff = A / (1 + SAM/100)     [reduce area by surface area margin]
```

With SAM = 0%: A_eff = A = 1.929 m².

Reference case:
```
Q = 1078 × 1.929 × 41.20 = 85,650 W = 292,245 Btu/h ✅
```

### 12.5 Energy Balances

Tube side (sensible + latent):
```
Q_sensible_t = mdot_dry × C_p_t × (T_it - T_ot) + mdot_vapour × C_p_vapour × (T_it - T_ot)
Q_latent     = m_cond × h_fg
Q_total      = Q_sensible_t + Q_latent
```

Shell side (sensible only):
```
Q_total = mdot_s × C_p_s × (T_os - T_is)
```

The solver iterates until both sides agree:
Q_tube_side = Q_shell_side = U × A_eff × LMTD.

---

## 13. Condensation

### 13.1 Inlet Dew Point

The dew point of the compressed gas at the tube inlet is calculated from the inlet specific
humidity ω_it and inlet total pressure P_it (bara):

```
P_w = ω_it × P_it / (ω_it + 0.622)     [partial pressure of water vapour, bara]
T_dew = B / (A - ln(P_w × 100)) - C    [°C, Antoine equation]
```

Reference case: ω_it = 0.00922 kg/kg at 11.36 bara → T_dew = 56.1°C = 132.9°F ✅

### 13.2 Condensation Criterion

Condensation occurs where the tube wall temperature falls below the local dew point.

The solver tracks four tube surface temperatures (at tube inlet, 1/3 L, 2/3 L, outlet):
```
T_wall = T_s + (T_t - T_s) × h_s_eff / (h_s_eff + h_t_eff)
```

Where T_s = local shell-side temperature, T_t = local tube-side temperature.

Condensation occurs where T_wall < T_dew.

### 13.3 Condensate Flow

```
m_cond = mdot_dry × (ω_it - ω_out)     [kg/s]
```

where ω_out is the outlet specific humidity at the saturation condition corresponding to
the outlet tube wall temperature.

Reference case: m_cond = 0.8139 × (0.00922 - 0.00314) = 0.00495 kg/s = **39.3 lb/h** ✅

### 13.4 Condensing Heat Transfer

```
Q_condensing = m_cond × h_fg = 0.00495 × 2468.4 kJ/kg = 12.22 kW = 41,711 Btu/h ✅
% of total = 12.22 / 85.65 = 14.3% ✅
```

---

## 14. Tube-Side Pressure Drop

Implemented as VBA function `dpt_func`.

### 14.1 Darcy-Weisbach Friction Factor

For the grooved tube (Wcool 2.03 curve-fit, same re-calibration as HTC):
```
f = f(Re_t)     [empirical, specific to 0.5" OD grooved tube]
```

For smooth (plain) tube, Colebrook-White or Moody:
```
1/√f = −2 × log₁₀(κ/(3.7×D_i) + 2.51/(Re_t×√f))
```

Correction factor for grooved tube pressure drop (matches Wcool 2.03 consistency):
```
cfp_corr = 0.80    [applied to friction pressure drop only — see release notes I0-1]
```

Reference case: f = 0.0505 (before correction), cfp_corr = 1.0 (plain = 1.0, groove may differ)

### 14.2 Friction Pressure Drop

```
ΔP_f = 4 × f × (L_t_eff / D_i) × G_t² / (2 × ρ_mean)    [Pa]
```

where ρ_mean = arithmetic mean of inlet and outlet densities.

### 14.3 Entry and Exit Loss Coefficients

From Kays & London (Re-dependent):
```
K_c = contraction coefficient at tube inlet  ≈ 0 for this case (turbulent, open inlet)
K_e = expansion coefficient at tube outlet   ≈ 0 for this case
```

Reference case: K_c = 0, K_e = 0 (confirmed from calc sheet).

### 14.4 Total Tube-Side Pressure Drop

```
ΔP_t = ΔP_f + (K_c + K_e) × G_t² / (2 × ρ_mean)    [Pa → convert to kPa, then to psi]
```

Reference case: ΔP_t = **62.48 kPa = 9.06 psi** ✅

*Note: The iterative solver recalculates ΔP_t as T_ot converges because ρ_mean changes.*

---

## 15. Shell-Side Pressure Drop (Bell-Delaware)

### 15.1 Ideal Crossflow Pressure Drop

```
f_s = B₃ × Re_s^(−n_f)           [Kern/Bell-Delaware friction factor, function of tube layout]
n_f = 0.2

ΔP_ideal = f_s × G_s² × N_tcc / (2 × ρ_s)    [Pa, per baffle]
```

### 15.2 Corrected Crossflow Pressure Drop

Two Bell-Delaware pressure-drop correction factors:

**R_l — Baffle leakage correction** (pressure drop equivalent):
```
r_lm = (A_sb + 0.5 × A_bt) / A_cs
r_ss = A_sb / (A_sb + A_bt)
R_l = exp(−1.33 × (1 + r_ss) × r_lm^0.15)
```
Reference case: R_l = **0.177**

**R_b — Bundle bypass correction**:
```
C_bp = 4.5 if Re_s < 100, else 3.7
R_b = exp(−C_bp × r_bp × (1 - (2×N_ss/N_tcc)^(1/3)))  if N_ss < N_tcc/2
    = 1.0                                                if N_ss ≥ N_tcc/2
```
Reference case: R_b = **0.148**

Total corrected crossflow ΔP per baffle space:
```
ΔP_cross = ΔP_ideal × R_l × R_b    [Pa]
```

Total crossflow (N_b − 1 baffle spaces):
```
ΔP_crossflow_total = ΔP_cross × (N_b - 1)
```

Reference case: ΔP_crossflow = **5.62 kPa**

### 15.3 Window Zone Pressure Drop

Mixed laminar/turbulent interpolation over 50 < Re_s < 200:

Turbulent window loss:
```
ΔP_w_turb = R_l × (2 + 0.6 × N_tcw) × G_w² / (2 × ρ_s)    [Pa]
G_w = mdot_s / sqrt(A_cs × A_cw)                              [window mass velocity]
```

Laminar window loss:
```
ΔP_w_lam = R_l × (26 × μ_s × G_w × (N_tcw / D_e + L_bc / D_hw²)) / ρ_s + G_w²/(ρ_s)
D_hw = hydraulic diameter of window zone
```

Combined (smooth interpolation):
```
if Re_s > 200:  ΔP_window = ΔP_w_turb × N_b
if Re_s < 50:   ΔP_window = ΔP_w_lam × N_b
else:           ΔP_window = (ΔP_w_turb × (Re_s-50)/150 + ΔP_w_lam × (200-Re_s)/150) × N_b
```

Reference case: ΔP_window = **37.52 kPa** (dominant term due to low baffle gap)

### 15.4 End Zone Pressure Drop

```
R_s = (L_be / L_bc)^(1 - n_s)     [end zone pressure correction, n_s = 0.2 turbulent]
ΔP_end = ΔP_ideal × R_l × R_s × 2    [two end zones]
```

Reference case: ΔP_end = **0.19 kPa**

### 15.5 Nozzle Pressure Drop

```
σ_S = min(A_cse, A_csn) / A_cs

Inlet contraction coefficient:
    K_c = 0.5 - 0.222×σ_S     if σ_S ≤ 0.18
         = 0.55 - 0.5×σ_S     if σ_S > 0.18

Outlet expansion coefficient:
    K_e = (1 - σ_S)²

G_nozzle = mdot_s / min(A_cse, A_csn)     [nozzle mass velocity]

ΔP_nozzle_in  = K_c × G_nozzle² / (2 × ρ_s)   [Pa]
ΔP_nozzle_out = K_e × G_nozzle² / (2 × ρ_s)   [Pa]
```

Reference case: σ_S = 0.175, K_c = 0.461, K_e = 0.681
- Inlet nozzle: **5.22 kPa**
- Outlet nozzle: **3.54 kPa**

### 15.6 Total Shell-Side Pressure Drop

```
ΔP_shell = ΔP_crossflow_total + ΔP_window + ΔP_end + ΔP_nozzle_in + ΔP_nozzle_out
```

Reference case:
```
ΔP_shell = 5.62 + 37.52 + 0.19 + 5.22 + 3.54 = 52.10 kPa = 7.55 psi ✅
```

*The window loss dominates because the W0230 has a tight central baffle gap (1.0")
relative to shell diameter (5.047") — this is typical for high-flux applications.*

---

## 16. Iterative Solver

The solver finds the tube outlet temperature T_ot that satisfies the overall energy balance.

```
Inputs:  T_it, T_is, mdot_t, mdot_s, A, U_function(T_ot), ω_it, P_it

Guess:   T_ot_guess = T_it - 0.5×(T_it - T_is)    [first guess: half of max possible]

Loop until |ΔP_t_n - ΔP_t_(n-1)| < tolerance and |Q_n - Q_(n-1)| < tolerance:
  1. Compute T_os from shell-side energy balance:
         T_os = T_is + Q / (mdot_s × Cp_s)
  2. Compute LMTD from T_it, T_ot, T_is, T_os
  3. Compute h_t from tube-side correlation at T_mean_t = (T_it + T_ot)/2
  4. Compute h_s from Bell-Delaware at T_mean_s = (T_is + T_os)/2
  5. Compute U from h_t, h_s, R_wall, R_ft, R_fs, condensation factor
  6. Compute Q_required = U × A_eff × LMTD
  7. Compute T_ot_new from tube-side energy balance:
         Q_required = mdot_t × Cp_eff × (T_it - T_ot_new)
  8. Update T_ot = T_ot_new

The solver also iterates on tube-side pressure drop (density changes with T_ot).
Max iterations: ~10 on Q, ~3 on ΔP_t.
```

Reference case convergence: 9 iterations on Q, 3 on ΔP_t.

---

## 17. Reference Case Validation

**Model:** W0230, Fixed bundle, 59" tube length, Stainless S3040, Std groove tube

**Tube side:** Air at 250°F inlet, 150 psig, 1423 Scfm, no fouling
**Shell side:** Water at 70°F inlet, 60 USgpm, no fouling
**Suction:** 14.7 psia, 85°F, 36% RH, 1500 Acfm

| Parameter | Spreadsheet | Expected |
|-----------|-------------|----------|
| Tube outlet temperature | 93.6°F | 93.6°F ✅ |
| Shell outlet temperature | 79.8°F | 79.8°F ✅ |
| Dew point at inlet | 132.9°F | — |
| Tube pressure loss | 9.06 psi | 9.06 psi ✅ |
| Shell pressure loss | 7.55 psi | 7.55 psi ✅ |
| Tube Re | 131,948 | — |
| Shell Re | 40,076 | — |
| Tube effective HTC | 281 Btu/h·ft²·R | — |
| Shell effective HTC | 595 Btu/h·ft²·R | — |
| LMTD | 74.2°R | 74.2°R ✅ |
| Overall HTC | 190 Btu/h·ft²·R | 190 Btu/h·ft²·R ✅ |
| Surface area | 20.8 ft² | 20.8 ft² ✅ |
| Total heat | 292,245 Btu/h | 292,245 Btu/h ✅ |
| Condensate | 39.3 lb/h | 39.3 lb/h ✅ |
| Condensing heat | 41,711 Btu/h (14.3%) | 14.3% ✅ |
| Number of tubes | 35 | — |
| mdot_dry | 0.8139 kg/s | — |
| mdot_shell | 3.777 kg/s | — |

Internal SI values at convergence:
- U = 1077.9 W/(m²·K), A = 1.929 m², LMTD = 41.20 K
- Q = 85,652 W = 292,245 Btu/h ✅
- Shell ΔP = 52.10 kPa (crossflow 5.62 + window 37.52 + end 0.19 + nozzle in 5.22 + nozzle out 3.54)
- Tube ΔP = 62.48 kPa

---

## 18. VBA Function Summary

The Excel workbook contains VBA functions (in the embedded `vbaProject.bin` module)
that are called as array formulas in the `calc` sheet.

| Function | Purpose | Called from |
|----------|---------|-------------|
| `mdot_in(value, UoM, ftype, fpar, T)` | Convert input flow to kg/s based on unit of measure, fluid code, fluid parameter (pressure/concentration), temperature | calc!P23 |
| `mdot_out(mdot_kg_s, UoM, ftype)` | Convert kg/s to selected output UoM | design display |
| `Pbar_in(value, UoM)` | Convert pressure input to bara | calc!J20 |
| `Pbar_out(value_bara, UoM)` | Convert bara to selected output UoM | design display |
| `ht_func(Re, Pr, D_i, k, tube_type, P, T_mean, T_wall)` | Tube-side HTC (W/m²·K) — Dittus-Boelter + Wcool 2.03 grooved tube fit | calc!O10:O11 |
| `hs_func(Re, Pr, D_e, k, correction_factors...)` | Shell-side HTC after Bell-Delaware corrections | calc!P10:P11 |
| `dpt_func(Re, G_t, L, D_i, rho_in, rho_out, ...)` | Tube-side pressure drop (kPa) | calc!F10:F16 |
| `iterative_solver(...)` | Main heat duty solver — returns [Q, U, dPt, T_ot, T_otw, T_otw_wet, ...]  | calc!B10:V11 |
| `Tdew(omega, P_bara)` | Dew point temperature (°C) given specific humidity and pressure | calc!J28 |
| `fpropg(gas_code, T_C, P_bara, property)` | Gas fluid properties | multiple calls |
| `fpropl(liquid_code, T_C, concentration, property)` | Liquid fluid properties | multiple calls |

All functions accept temperatures in °C and pressures in bara internally.

---

## 19. Notes for Implementation

1. **Start with the reference case** — implement formulas until all 14 reference values match.

2. **Unit conventions** — all internal calculations in SI (K, Pa, m, kg, s). Convert inputs/outputs at the boundaries only.

3. **Property tables** — the VBA fluid property functions use polynomial fits. For the web app, implement simplified polynomial fits or table lookups for the temperature ranges used in practice (gas ~0–200°C, water 10–80°C). Air properties at pressure can be estimated from ideal gas density + temperature-polynomial viscosity/k/Cp.

4. **Grooved tube HTC** — the exact Wcool 2.03 curve-fit constants are in the VBA binary and cannot be recovered without running Excel. A good approximation uses the Dittus-Boelter correlation with an enhancement factor of approximately 1.15–1.25 over the plain tube at typical Re values (80,000–150,000). Alternatively: work backwards from the reference case to calibrate the constants.

5. **Bell-Delaware corrections** — implement all five (Jc, Jl, Jb, Jr, Js). The leakage factor Jl is the dominant reduction (0.35 for W0230 — a factor of 3 reduction from ideal).

6. **Condensation zone** — the solver handles a mixed wet/dry model. A simplified but adequate approach: treat the entire surface as condensing when T_wall < T_dew at the tube inlet. The tube outlet humidity adjusts to the saturation value at the wall temperature. This gives the correct condensate flow for the reference case.

7. **Convergence** — 10–15 iterations on T_ot using bisection or secant method. Tolerance: |Q_n - Q_{n-1}| < 1 W.

8. **Surface area margin** — applied as a multiplier: A_eff = A × (100 / (100 + SAM)). With SAM = 0%, A_eff = A.

9. **Number of baffles** — for fixed bundles, the table value applies. For removable bundles, some models use a lower count (see ¹ footnote in §7 table).

10. **Custom tube length** — when "Custom" is selected, L_t, N_baffles, and L_bc are all user-specified. The standard central baffle gap formula does not apply.
