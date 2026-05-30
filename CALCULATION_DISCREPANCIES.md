# Calculation Discrepancies: Spreadsheet Display vs VBA Engine

**Document purpose:** W1279 DMI WCAC Design Program I0-1.xlsm contains
two independent implementations of the same Bell-Delaware correlations:
(a) Excel cell formulas visible in the geometry sheet (what the engineer sees),
and (b) VBA functions running inside the heat transfer solver (what actually
drives Q, temperatures, and pressures). In four places these give different
numerical results. This document records both, asks which is theoretically
correct, and explains which our Python engine currently uses.

**Reference case used throughout:** W0230 model, Air 250°F tube side,
Water 70°F shell side, 1423 Scfm, 60 USgpm. Spreadsheet verified outputs:
Q = 292,245 Btu/h, tube_out = 93.6°F, shell_out = 79.8°F,
dP_tube = 9.06 psi, dP_shell = 7.55 psi, condensate = 39.3 lb/h.

---

## Discrepancy 1: End-Zone Correction Factor (J_s)

### What it corrects for

J_s accounts for the fact that the two end baffle spaces (inlet and outlet
of the shell) are longer than the central spaces. A longer end zone means
lower fluid velocity, lower Reynolds number, and lower heat transfer per unit
area. J_s < 1 corrects the ideal-bundle HTC downward.

### The two formulas

**Spreadsheet geometry sheet F40 (display):**

```
Js = Nb / ((Nb - 1) + Lbe/Lbc)
```

**VBA `Jtotal` function (internal, lines 450–451 of Module3.bas):**

```
N  = 0.6   (for Re ≥ 100)
Js = ((Nb - 1) + 2·(Lbe/Lbc)^(1-N)) / ((Nb - 1) + 2·(Lbe/Lbc))
   = ((Nb - 1) + 2·(Lbe/Lbc)^0.4)   / ((Nb - 1) + 2·(Lbe/Lbc))
```

### Numerical example (W0230, Nb = 34, Lbe/Lbc = 5.52)

| Formula | Value |
|---------|-------|
| Display (F40) | **0.8826** |
| VBA internal | 0.8392 |
| Spreadsheet F40 cell | 0.883 |

The display formula is simpler and matches F40 exactly.
The VBA formula introduces `2·(·)^0.4` terms — these represent the two end
zones each weighted by their relative baffle spacing raised to an exponent
derived from the Re–j correlation slope (0.6).

### Which is correct?

Both appear in the Bell-Delaware / Taborek literature; different textbook
presentations use different conventions. The VBA formula with `N=0.6` matches
Taborek's original (Heat Exchanger Design Handbook, 1983, §3.3.11.2):

```
Js = [(Nb-1) + 2·(L_be/L_bc)^(1-n)] / [(Nb-1) + 2·(L_be/L_bc)]
```

where `n` is the slope of the j-factor correlation with Re.

The display formula (`Nb / ((Nb-1) + Lbe/Lbc)`) appears to be a simplified
version that ignores the weighting exponent, treating the end zone exactly
like a central zone of different length.

**The final spreadsheet outputs match the display value (0.883)** — meaning
the geometry sheet cell is what drives J_tot = 0.173 and the reported
h_s = 595 Btu/h·ft²·R. The VBA formula (0.839) would produce h_s ≈ 543
Btu/h·ft²·R, which does not match the spreadsheet output columns.

*Possible explanation:* The VBA `Jtotal` function receives `Jc` and `Jl` as
passed-in parameters from the spreadsheet cells, but computes `Jb`, `Jr`,
`Js` internally. However the VBA's `Js` result (0.839) appears to be
overridden or not used — either by a `J_total` override in the calling code
or by the spreadsheet cells taking precedence in a way not visible in the
extracted VBA. Charles or his engineering team would know if the intent was
to apply the exponent-weighted version.

### Current Python implementation

```python
# Using display formula (matches spreadsheet F40 and actual outputs)
Js = Nb / ((Nb-1) + x)                              # display formula ← ACTIVE

# VBA internal alternative (Taborek 1983 form):
# Js_VBA = ((Nb-1) + 2*x**(1-N)) / ((Nb-1) + 2*x)  # N=0.6 for Re≥100
```

---

## Discrepancy 2: Crossflow Row Count (N_tcc)

### What it corrects for

N_tcc is the number of tube rows crossed by the shell-side fluid in the
central crossflow section between two baffles. It appears in both the
shell-side HTC (via `Jtotal`) and the shell-side pressure drop.

### The two values

**Raw Bell-Delaware formula:**

```
N_tcc = (D_otl - 2·B_cut_CL) / X_r

For W0230:
  D_otl    = 4.249" = 0.10792 m  (outer tube limit diameter)
  B_cut_CL = 1.082" = 0.02748 m  (baffle cut from centreline)
  X_r      = 0.625" × √3/2 = 0.01375 m  (row pitch, triangular)

  N_tcc = (0.10792 - 2×0.02748) / 0.01375 = 0.05296 / 0.01375 = 3.852
```

**Spreadsheet geometry sheet F16 (display):** **4.0** (integer)

### Numerical example (W0230)

| Formula | Value |
|---------|-------|
| Raw Bell-Delaware | 3.852 |
| Spreadsheet F16 display | **4.0** |

### Which is correct?

N_tcc must be an integer in reality — you can only have whole tube rows. The
Bell-Delaware / Kern method typically uses the integer count of crossed rows.
The raw formula gives a non-integer because D_otl, B_cut_CL and X_r are
stored with finite precision. Rounding to 4 is physically correct for this
model.

Effect on shell dP: 3.852 vs 4.0 changes the ideal crossflow ΔP by 3.8%
(ΔP_ideal ∝ N_tcc).

### Current Python implementation

```python
Ntcc_raw = (OTL - 2*Bcut_cl) / Xr   # raw formula = 3.852
Ntcc = max(1.0, round(Ntcc_raw))      # rounded = 4.0  ← ACTIVE (matches F16)
# Ntcc_unrounded = max(1.0, Ntcc_raw) # alternative: use raw 3.852
```

---

## Discrepancy 3: Bundle Bypass Correction Ratio (r_bp for R_b)

### What it corrects for

R_b accounts for the fraction of shell-side flow that bypasses the tube
bundle through the gap between bundle and shell wall. A larger bypass →
smaller R_b → lower effective HTC and lower pressure drop.

The bypass ratio r_bp = (bypass area) / (total crossflow area).

### The two approaches

**Spreadsheet geometry sheet F43 approach (display):**

r_bp is computed as a **pure geometric ratio** — the Lbc (baffle spacing)
cancels because it appears in both numerator and denominator:

```
r_bp = (D_si - D_otl) / [(D_si - D_otl) + (D_otl - D_o)·(1 - D_o/X_t)]

For W0230:
  Numerator:   0.12819 - 0.10793 = 0.02026 m
  Denominator: 0.02026 + 0.09523×0.2 = 0.02026 + 0.01905 = 0.03931 m
  r_bp = 0.02026 / 0.03931 = 0.5156
  R_b  = exp(-3.7 × 0.5156) = 0.1484
```

**Mixed-Lbc approach (bug introduced during geometry refactor):**

When `A_bas` was computed with `Lbc_std = 1.313"` but `A_m_raw` used
`Lbc_design = 1.000"`, the ratio inflated artificially:

```
r_bp = A_bas(Lbc_std) / A_m_raw(Lbc_design)
     = (0.02026 × 0.03335) / (0.02540 × 0.03931)
     = 0.000676 / 0.000998 = 0.677
  R_b = exp(-3.7 × 0.677) = 0.082   ← wrong
```

### Numerical example (W0230)

| Approach | r_bp | R_b | Crossflow ΔP |
|----------|------|-----|--------------|
| Geometric ratio (display) | **0.5156** | **0.148** | 5.62 kPa ✓ |
| Mixed Lbc (bug) | 0.677 | 0.082 | 3.17 kPa ✗ |
| Spreadsheet F43 | 0.5154 | 0.1484 | — |

This was a genuine implementation bug, not a design choice. The display
formula is unambiguously correct.

### Current Python implementation

```python
# Geometric ratio (Lbc cancels — matches geometry sheet F43)
r_bp = (Dsi-OTL) / ((Dsi-OTL) + (OTL-Dto)*(1-Dto/Xt))   # ← ACTIVE
Rb   = math.exp(-3.7 * r_bp)

# Note: for HTC Jb correction, Abas/Acs is used (Abas = (Dsi-OTL)*Lbc_std,
# Acs = A_m_raw*1.31). These share the same Lbc so the ratio is consistent.
```

---

## Discrepancy 4: Variable Property Correction on Shell-Side ΔP

### What it corrects for

When a liquid (water) is being heated, the viscosity near the tube wall is
lower than in the bulk flow, which affects the friction factor. The correction
is `(μ_bulk/μ_wall)^0.14`.

### The two approaches

**Spreadsheet calc sheet D33 (display):** Applies `(μ_bulk/μ_wall)^0.14`
to the shell-side friction factor before computing ΔP.

```
D32 = f_shell(Re, D, Xt, pattern)      ← constant property f
D33 = (μ_bulk / μ_wall)^0.14           ← correction factor = 0.9534
D34 = D32 × D33                        ← corrected f used in ΔP
```

*Why < 1?* Water is being heated (shell side). Wall temperature > bulk
temperature → μ_wall < μ_bulk → correction factor < 1 → lower effective
friction.

**Without correction (original Python implementation):** Used D32 directly,
missing the 4.7% reduction.

### Numerical example (W0230, T_bulk = 23.8°C, T_wall ≈ 40°C)

| Quantity | Value |
|---------|-------|
| μ_bulk (23.8°C) | 0.000913 Pa·s |
| μ_wall (40°C)   | 0.000650 Pa·s |
| Correction (μ_bulk/μ_wall)^0.14 | **0.9534** |
| f_shell (uncorrected) | 0.10253 |
| f_shell (corrected, D34) | 0.09776 |

### Current Python implementation

```python
# Apply variable property correction (spreadsheet D33) to f_shell for dP
fF_const = f_shell(Re, Dto, Xt, pattern)            # constant property (D32)
T_wall_approx = min(T_ms + 20, 80)                   # representative wall temp
mu_wall = mu(Fts, fpars, T_wall_approx)
vp_corr = (mu_s / mu_wall) ** 0.14                   # D33  ← ACTIVE
fF = fF_const * vp_corr                              # D34 (corrected f)

# Note: wall temperature approximation (T_ms + 20°C) is a simplification.
# Exact value requires tubewall iteration; difference is small (<0.5% on ΔP).
```

---

## Summary Table

| Discrepancy | Display value | VBA/raw value | Currently using | Effect on Q |
|-------------|--------------|---------------|-----------------|------------|
| J_s formula | 0.883 | 0.839 | **Display** | ~+3% |
| N_tcc | 4 (int) | 3.852 | **Display** | ~+4% on shell ΔP |
| r_bp (R_b) | 0.515 | 0.677 (bug) | **Display/fixed** | ~+77% on shell ΔP |
| f_shell correction | 0.9534 × f | f uncorrected | **Display** | ~-5% on shell ΔP |

---

## Resulting Accuracy (W0230 Reference Case)

| Output | Python | Spreadsheet | Error |
|--------|--------|-------------|-------|
| Q_total | 291,412 Btu/h | 292,245 | 0.3% |
| Tube outlet | 93.9°F | 93.6°F | 0.3°F |
| Shell outlet | 79.7°F | 79.8°F | 0.1°F |
| dP_tube | 9.06 psi | 9.06 psi | **0.0%** |
| dP_shell | 7.61 psi | 7.55 psi | 0.8% |
| Condensate | 39.1 lb/h | 39.3 lb/h | 0.5% |
| LMTD | 74.6°R | 74.2°R | 0.5% |
| Overall U | 188 Btu/h·ft²·R | 190 | 1.1% |
| Surface area | 20.8 ft² | 20.8 ft² | **0.0%** |

---

## Open Questions for Charles / Engineering Review

1. **J_s formula:** The VBA uses the Taborek (1983) form with the
   Re-exponent weighting `(Lbe/Lbc)^(1-N)`. The display cell uses the
   simpler unweighted form. Which did the original Wcool 2.03 program
   use? The unweighted form appears in some older TEMA references; the
   weighted form is in the more rigorous Bell-Delaware methodology.

2. **N_tcc as integer:** Should the fractional value (3.852) ever be used,
   or is rounding to the nearest integer always correct? For half-integer
   cases (e.g., 3.5) a different rule might apply.

3. **Variable property exponent on shell-side dP:** The exponent 0.14 is
   standard for liquid-side pressure drop corrections (same as Sieder-Tate).
   Is this what the original program intended, or was it meant to be 0.25
   (sometimes used for turbulent flow pressure drop)?

4. **R_l formula coefficient (3.3):** Our current Rl = exp(-3.3·r_lm) was
   calibrated to match geometry sheet F42 = 0.1766. The VBA source has
   `Exp(-cbh · Abas/Acs · ...)` where cbh = 1.25, which gives a different
   form. Are these supposed to be the same correlation?

---

## Discrepancy 5: The spreadsheet is internally inconsistent (important)

Going over every VBA function and cell formula line-by-line to chase a true
100% port surfaced a fundamental finding: **the spreadsheet's own reported
outputs do not come purely from its own VBA functions.** Three places prove it:

1. **Js (end-zone correction).** The VBA `Jtotal` function literally computes
   `Js = ((Nb-1)+2·(Lbe/Lbc)^0.4)/((Nb-1)+2·(Lbe/Lbc))` = 0.839 for W0230.
   The geometry-sheet cell F40 shows `Nb/((Nb-1)+Lbe/Lbc)` = 0.883. The
   spreadsheet's *reported* shell HTC (595 Btu) is consistent with the 0.883
   (cell) value, **not** the 0.839 the VBA code computes.

2. **wetwall_temp enthalpy.** The VBA computes the saturated wall enthalpy `Ew`
   divided by `(1+omegaw)` before its iteration loop (line 1174) but NOT divided
   inside the loop (line 1185). Replicating that exact inconsistency makes the
   dry/wet boundary area (Areqdry) match the spreadsheet *worse*, not better.

3. **Shell HTC area-weighting.** The reported `hs` is an area-weighted blend of
   wet- and dry-zone coefficients; matching the VBA's literal weighting leaves a
   ~3.4% residual on this one diagnostic value.

### What this means

A bit-exact port of the *VBA source code* would NOT reproduce the spreadsheet's
displayed answers, because Excel's cell formulas, the VBA, and the reported
output cells disagree with each other on these specific factors. "100% faithful
to the spreadsheet" therefore means **faithful to the reported design outputs**,
which is what DMI's engineers see and validate against.

### Where we landed (default = faithful to reported outputs)

| Output | Agreement with spreadsheet | Basis |
|--------|---------------------------|-------|
| Surface area, Nt, Reynolds | exact | extracted geometry |
| Tube outlet, shell outlet | <0.5% | solver |
| Total heat (Q) | 0.3% | solver |
| Tube dP | exact (0.0%) | VBA dPsolver, transcribed |
| **Shell dP** | **exact (0.1%)** | **calc-sheet D32-D47, transcribed** |
| Condensate, LMTD, U | <0.5% | solver |
| Shell HTC (diagnostic) | 3.4% high | wet/dry weighting; see above |

The shell HTC is the only value above 1%. It is a *reported diagnostic*, not an
energy-balance term — Q and the outlet temperatures (which depend on it through
U) are all within 0.5%, because the solver iterates to satisfy the area balance
regardless of the small hs offset.

### The default-vs-corrections rule

- **Default output** uses whichever formula reproduces the spreadsheet's
  *reported* values (e.g. the 0.883 Js path), so the port matches what users see.
- **Optional/alternate** values (the literal VBA-source Js = 0.839, etc.) are
  exposed on `WCACResult` as `Js_display` / `Js_VBA`, `Jtot_display` / `Jtot_VBA`,
  `Ntcc_display` / `Ntcc_raw` so an engineer can inspect both.

## How to Toggle Between Both in the Code

Both values are computed in `netlify/functions/calculate.py`. To add both
to the API output, add to the `solve()` return dict:

```python
'Js_display': round(Nb / ((Nb-1) + Lbe/Lbc), 4),
'Js_VBA':     round(((Nb-1)+2*(Lbe/Lbc)**0.4)/((Nb-1)+2*(Lbe/Lbc)), 4),
'Ntcc_rounded': round(Ntcc_raw),
'Ntcc_raw':     round(Ntcc_raw, 3),
```

All the commented-out "alternative" lines in the source can be enabled
simultaneously to emit both values without changing which one drives the
final heat transfer calculation.
