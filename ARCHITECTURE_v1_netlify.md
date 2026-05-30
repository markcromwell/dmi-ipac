# DMI-IPAC Architecture Contract

DMI Integrated Performance Analysis Calculator â€” web replacement for the W1279 WCAC Excel design tool used by Diversified Manufacturing Inc.

## 1. Topology

Two-tier static + serverless application:

- **Frontend** (publicly readable) â€” `public/` directory served at site root by Netlify CDN. Pure HTML/JS/CSS with no build step. All third-party libs loaded via CDN. Responsibility: collect inputs, POST JSON to backend, render returned JSON into a results table and downloadable PDF.
- **Backend** (proprietary) â€” `netlify/functions/calculate.py`, a single Python file using stdlib only. Responsibility: ALL heat-transfer, pressure-drop, and thermal-solver logic. No proprietary calculation logic may exist anywhere outside this file.

The frontend reaches the backend at `/.netlify/functions/calculate` via HTTPS POST with `Content-Type: application/json`.

## 2. Directory Layout

```
/
â”œâ”€â”€ ARCHITECTURE.md              # Binding architecture contract (this document)
â”œâ”€â”€ validate.py                  # Repo-root validation gate (CI / agent gate)
â”œâ”€â”€ netlify.toml                 # Netlify build & function config
â”œâ”€â”€ README.md                    # Project overview, run/test/deploy commands
â”œâ”€â”€ .gitignore
â”œâ”€â”€ public/                      # Static site root (Netlify `publish` dir)
â”‚   â”œâ”€â”€ index.html               # Single-page UI shell
â”‚   â”œâ”€â”€ app.js                   # Form handling, fetch(), results rendering
â”‚   â”œâ”€â”€ pdf.js                   # jsPDF datasheet generator
â”‚   â””â”€â”€ styles.css               # Custom CSS overrides only (Tailwind via CDN)
â”œâ”€â”€ netlify/
â”‚   â””â”€â”€ functions/
â”‚       â””â”€â”€ calculate.py         # PROPRIETARY: all calculation logic, single file
â””â”€â”€ tests/
    â”œâ”€â”€ __init__.py
    â”œâ”€â”€ test_calculate.py        # Unit tests + W0230 reference case
    â”œâ”€â”€ test_handler.py          # Handler I/O contract tests
    â””â”€â”€ fixtures/
        â””â”€â”€ reference_w0230.json # Expected outputs for the W0230 reference case
```

Folder purposes:
- `public/` â€” everything here is shipped to browsers. Contains NO proprietary math.
- `netlify/functions/` â€” server code. The single file `calculate.py` owns all calculation IP. No additional `.py` files are permitted in this folder.
- `tests/` â€” Python `unittest` suite, runnable with stdlib only.

## 3. Backend Module Contract (`netlify/functions/calculate.py`)

Single file, Python 3.11 stdlib only (`json`, `math`, `decimal` if needed). No external pip dependencies, no `requirements.txt`.

### Public Entry Point

```python
def handler(event, context):
    """Netlify Functions entry point (AWS-Lambda compatible).
    Returns {'statusCode': int, 'headers': dict, 'body': str} where body is JSON.
    """
```

### Required Internal Sections (in this order within the file)

1. **Constants** â€” physical constants, unit conversions, solver tolerances (`REL_TOL = 1e-4`, `MAX_ITERS = 100`).
2. **Input validation** â€” `parse_inputs(raw_body: dict) -> dict`. Raises `ValueError` with a stable error code string on malformed input.
3. **Fluid properties** â€”
   - `air_properties(T_F: float, P_psig: float) -> dict`
   - `water_properties(T_F: float) -> dict`
   Each returns a dict with keys: `rho` (lb/ftÂ³), `cp` (Btu/lbÂ·Â°F), `mu` (lb/ftÂ·h), `k` (Btu/hÂ·ftÂ·Â°F), `pr` (dimensionless).
4. **Heat transfer coefficients** â€”
   - `dittus_boelter_tube_htc(Re, Pr, k_fluid, D_i_ft, heating: bool) -> float` returns Btu/hÂ·ftÂ²Â·Â°F.
   - `bell_delaware_shell_htc(geom: dict, flow: dict, props: dict) -> float` returns Btu/hÂ·ftÂ²Â·Â°F.
5. **Pressure drops** â€”
   - `pressure_drop_tube(...)` returns psi.
   - `pressure_drop_shell_bell_delaware(...)` returns psi.
6. **Thermal solver** â€” `solve_thermal(inputs: dict) -> dict`. Iterates outlet temperatures until energy balance converges (`rel tol 1e-4`, max 100 iterations).
7. **Output formatter** â€” `build_response(solved: dict, echo: dict) -> dict`.
8. **Handler** â€” wires the above and returns the AWS-Lambda response shape.

### Naming Conventions (Backend)

- `snake_case` for function and variable names.
- Units are encoded in identifier suffixes: temperatures `_F`, pressures `_psig` or `_psi`, flows `_usgpm` or `_scfm`, lengths `_ft` or `_in`.
- Every public function has type hints and a one-line docstring stating units of all inputs and outputs.

## 4. Frontend Module Contract (`public/`)

### `index.html`

- Loads Tailwind via `https://cdn.tailwindcss.com`.
- Loads jsPDF via `https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`.
- Loads `./app.js` and `./pdf.js` as plain `<script>` tags. No ES modules, no bundler, no transpile.
- Contains exactly one `<form id="inputForm">` and one `<section id="resultsSection" hidden>`.
- Element IDs use `camelCase` (e.g., `tubeInletTempF`, `shellFlowUsgpm`, `runButton`, `downloadPdfButton`, `modelSelect`).

### `app.js`

- Exposes globals: `collectInputs()`, `submitCalculation()`, `renderResults(json)`, `showError(msg)`.
- Single fetch target: `POST /.netlify/functions/calculate`.
- On success, calls `renderResults(json)` then enables the Download PDF button which invokes `generateDatasheetPdf(...)`.
- **MUST NOT** contain Bell-Delaware, Dittus-Boelter, Reynolds, Prandtl, Nusselt, or any heat-transfer or pressure-drop formula.
- Only allowed math: display formatting, unit conversion for UI labels, and trivial input scaling (e.g., percent display).

### `pdf.js`

- Exposes global: `generateDatasheetPdf(resultsJson, inputsJson)`.
- Renders a single-page datasheet using jsPDF text and table primitives, mirroring the W1279 layout.
- Pure presentation â€” consumes already-solved values, performs no calculations.

### Frontend Naming Conventions

- `camelCase` for JS functions, variables, and HTML element IDs.
- File names lowercase, no spaces, no underscores in `public/`.
- CSS classes: Tailwind utilities preferred; custom classes use `kebab-case` and live only in `public/styles.css`.

## 5. Wire Contract (Frontend â†” Backend)

### Request â€” `POST /.netlify/functions/calculate`
```json
{
  "model": "W0230",
  "tube_side": {
    "fluid": "air",
    "inlet_temp_F": 250.0,
    "inlet_pressure_psig": 150.0,
    "flow_rate_scfm": 0.0
  },
  "shell_side": {
    "fluid": "water",
    "inlet_temp_F": 70.0,
    "flow_rate_usgpm": 60.0
  },
  "geometry_overrides": {}
}
```

### Success Response (HTTP 200)
```json
{
  "ok": true,
  "inputs_echo": { },
  "results": {
    "Q_BtuPerHr": 292245,
    "tube_outlet_F": 93.6,
    "shell_outlet_F": 79.8,
    "dP_tube_psi": 9.06,
    "dP_shell_psi": 7.55,
    "U_BtuPerHrFt2F": 0,
    "iterations": 0,
    "converged": true
  },
  "diagnostics": { }
}
```

### Error Response (HTTP 4xx/5xx)
```json
{ "ok": false, "error": { "code": "INVALID_INPUT", "message": "..." } }
```

Response field names are STABLE. Frontend code MUST read these exact keys; backend code MUST emit these exact keys.

## 6. Reference Case (Validation Anchor)

Model W0230, tube-side Air at 150 psig / 250Â°F, shell-side Water at 70Â°F / 60 USgpm.

Expected outputs (Â±0.5% tolerance):
- `Q_BtuPerHr` â‰ˆ 292245
- `tube_outlet_F` â‰ˆ 93.6
- `shell_outlet_F` â‰ˆ 79.8
- `dP_tube_psi` â‰ˆ 9.06
- `dP_shell_psi` â‰ˆ 7.55

This case is the single source of truth for solver correctness. `tests/fixtures/reference_w0230.json` is the contract; do not edit its expected values without explicit user approval. Any spec that changes solver code MUST keep this test green.

## 7. Build, Test, Deploy Tooling

- **Build**: none. `netlify.toml` declares `publish = "public"` and `functions = "netlify/functions"`.
- **Test**: `python -m unittest discover -s tests -v` (Python 3.11+ stdlib only).
- **Validation gate**: `python validate.py` at repo root â€” checks structure, enforces proprietary isolation, runs tests.
- **Local dev**: `netlify dev` (Netlify CLI). No other local server required.
- **Deploy**: auto on push to `main` via Netlify GitHub integration. Free tier.

## 8. Hard Architectural Rules (NON-NEGOTIABLE)

1. **Proprietary isolation** â€” no file in `public/` may contain any of these case-insensitive substrings: `bell_delaware`, `belldelaware`, `dittus_boelter`, `dittusboelter`, `reynolds`, `prandtl`, `nusselt`, `htc`. `validate.py` enforces this and fails the build on violation.
2. **Single calc file** â€” `netlify/functions/calculate.py` is the ONLY file in `netlify/functions/`. No helper modules, no `utils.py`, no subpackages.
3. **Stdlib only** â€” no `requirements.txt`, no `package.json`, no `node_modules/`. CDN-only frontend deps.
4. **No build step** â€” `public/index.html` must run directly from disk when served by `netlify dev` with zero transpile.
5. **Reference case is binding** â€” `tests/fixtures/reference_w0230.json` defines correctness. Modifying its expected values requires explicit user approval.
6. **Stable wire contract** â€” request and response key names from Â§5 are frozen; new fields may be ADDED but existing keys may not be renamed or removed.
7. **Naming discipline** â€” backend `snake_case`, frontend `camelCase`, file names lowercase. Mixing styles is a contract violation.
