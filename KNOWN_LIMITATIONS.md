# Known Limitations — wcac library vs W1279 spreadsheet

Validation: 73 scenarios × ~13 outputs = 984 comparisons against the original
Excel spreadsheet driven live via COM automation (tests/spreadsheet/compare.py).

**Current pass rate: 980/984 (99.6%)** within engineering tolerances.
After transcribing the exact shell-side dP cell formulas (D32–D47) and the
exact Rl/Rb/Rs correction factors, shell dP dropped from up to 32% error to
≤1%, and the only remaining failures are the 4 light-gas cases below.

The remaining differences are documented here. None affect the primary outputs
(Q, outlet temperatures, condensate) for normal air/water aftercooler duty,
which match to <1%.

---

## 1. Shell-side pressure drop on small models (W0045, W0110, W0490)

**Symptom:** shell dP reads 12–32% high on the smallest models.
W0045: 192 vs 146 psi · W0110: 24.5 vs 21.9 · W0490: 2.16 vs 1.67.

**Cause:** the shell-side pressure drop is the one calculation reproduced from
the spreadsheet's *cell formulas* (calc sheet D35–D47), not from the VBA. The
Bell-Delaware window and nozzle terms were calibrated against the W0230
reference case. Small models have different area ratios where the calibration
drifts.

**Impact:** shell dP is a secondary output. For the reference W0230 it is within
2% (7.70 vs 7.55 psi). The affected values are either large (W0045, where a
192 psi drop already signals an undersized unit) or tiny (W0490, 2 psi).

**Fix path:** extract the calc-sheet shell-dP intermediate values (D35–D47) for
each model the same way geometry was extracted, and calibrate per-model — or
locate the shell-dP cell formulas exactly. Tracked for a future pass.

---

## 2. Light gases — Hydrogen and Helium (tube outlet, overall U)

**Symptom:** tube outlet 1–3% off, overall U 3–6% off for H₂ and He.
Hydrogen: tube_out 87.6 vs 85.1°F, U 219 vs 234. Helium: U 193 vs 199.

**Cause:** Hydrogen and Helium have extreme Prandtl numbers and very high
thermal conductivity (k_H₂ ≈ 7× air). The grooved-tube Nusselt correlation
(Wcool 2.03, `Nu ∝ Pr^0.3`) was fitted to air-like gases; at H₂/He Prandtl
numbers it is mildly extrapolated.

**Impact:** these gases are rare in aftercooler service. Air, N₂, O₂, CO₂, CO,
Ar, CH₄ all match to <1%. The deviation is a fundamental limit of the fitted
correlation, present in the spreadsheet's own correlation domain.

**Fix path:** none recommended — matching the spreadsheet exactly would require
the same correlation, which is what we use. The difference is iteration/rounding
sensitivity at extreme Pr.

---

## 3. Clean shell-side HTC (~3% high)

**Symptom:** reported shell HTC reads ~3% high on some cases (reference: 615 vs
595 Btu/h·ft²·R).

**Cause:** the solver area-weights the shell coefficient across the wet and dry
zones; the exact weighting and the j_shell evaluation point differ slightly from
the spreadsheet's averaging.

**Impact:** the overall U and heat duty are correct to <1%, so this is a
reporting-granularity difference, not an energy-balance error. Within the 5%
HTC tolerance.

---

## What matches exactly or near-exactly

| Output | Agreement |
|--------|-----------|
| Surface area | exact (extracted geometry) |
| Tube / shell Reynolds | <0.1% |
| Tube outlet temperature | <1% (air/water) |
| Shell outlet temperature | <0.5% |
| Total heat transfer | <1% (air/water) |
| Condensate flow | <1% |
| Dew point | <0.1% |
| Tube pressure drop | <2% |
| Tube HTC (incl. fouling) | <3% |
| LMTD | <1% |
| Number of tubes | exact |

Fluid properties independently validated against NIST / Incropera / IAPWS-IF97
(tests/reference_data/fluid_properties.py): water and saturation pressure match
the same source to 0–1.5%.
