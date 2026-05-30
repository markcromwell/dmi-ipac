# DMI-IPAC Architecture

> Supersedes the original two-tier Netlify contract, preserved as
> `ARCHITECTURE_v1_netlify.md`. The project is now a multi-target system built
> on a single shared physics library.

One physics engine, many front-ends. The proprietary calculation logic lives
in a single Python library (`wcac/`) and every deployment target imports or
calls it — the math is never duplicated and (for networked clients) never
leaves the server.

```
                        ┌─────────────────────────────┐
                        │   wcac/  (Python library)    │
                        │  - fluids, surface, solver   │   ← 50 yrs of DMI IP
                        │  - geometry, models, units   │     (Bell-Delaware,
                        │  - validation                │      Wcool 2.03, etc.)
                        │  - calculate() entry point   │
                        └──────────────┬──────────────┘
                                       │ import
          ┌────────────────┬───────────┼───────────┬──────────────────┐
          │                │           │           │                  │
     ┌────▼────┐     ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐      ┌──────▼───────┐
     │  CLI    │     │ Desktop   │ │ REST   │ │ (future) │      │  Spreadsheet │
     │ wcac_   │     │ GUI       │ │ API    │ │ batch /  │      │  validation  │
     │ cli.py  │     │ Tkinter   │ │FastAPI │ │ pipelines│      │  harness     │
     └─────────┘     └───────────┘ └───┬────┘ └──────────┘      └──────────────┘
      local           local            │ HTTP                    (tests, Excel
      (engine          (engine    ┌────┴─────┐                    COM oracle)
       on box)          on box)   │          │
                              ┌───▼───┐  ┌───▼─────┐
                              │  Web  │  │ Android │   ← engine stays server-side
                              │ front │  │  app    │     (proprietary IP safe)
                              │ end   │  │ Kotlin  │
                              └───────┘  └─────────┘
                                  │
                              ┌───▼──────────┐
                              │  SQLite /    │   saved designs
                              │  PostgreSQL  │   (inputs + results + metadata)
                              └──────────────┘
```

## Targets

| Target | Path | Engine location | Use case |
|--------|------|-----------------|----------|
| **Library** | `wcac/` | — | the single source of truth; import in any Python |
| **CLI** | `targets/cli/` | local | scripting, batch, datasheets from the terminal |
| **Desktop** | `targets/desktop/` | local | engineer's workstation (Windows/Mac, offline) |
| **REST API** | `targets/api/` | server | backend for web + mobile; validation + persistence |
| **Web** | `targets/web/` | server (via API) | browser access with saved designs |
| **Web (simple)** | `public/` + `netlify/` | server (Netlify fn) | the original lightweight Netlify deployment |
| **Android** | `targets/android/` | server (via API) | field/mobile access |
| **Database** | `targets/api/db.py` | server | save / retrieve / compare designs |

## Why this shape

- **IP protection.** The Bell-Delaware shell-side method, the Wcool 2.03
  grooved-tube correlations, and the two-zone condensing solver are DMI's
  proprietary engineering. Networked clients (web, mobile) never receive the
  code — they POST inputs and receive results. Local clients (CLI, desktop)
  run on trusted machines.

- **No duplicated math.** Every target uses the exact same `calculate()`. A
  fix to the physics propagates everywhere at once. The spreadsheet validation
  harness proves the one engine matches the original Excel to ~99.3%.

- **Shared validation.** `wcac/validation.py` is the single set of input guards
  (range limits, physical bounds). Every front-end enforces identical rules.

## The library (`wcac/`)

| Module | Responsibility | VBA origin |
|--------|----------------|------------|
| `fluids.py` | fluid properties (water, glycols, sea water, 9 gases), Pswater | Module1 |
| `surface.py` | tube/shell HTC & friction correlations, KcKe | Module2 |
| `solver.py` | Qsolver (two-zone), dPsolver, dew_point, tubewall, Jtotal | Module3 |
| `geometry.py` | bundle geometry + shell pressure drop | Module4 + cell formulas |
| `models.py` | model table W0035-W5000 | models sheet |
| `exact_geometry.py` | ground-truth geometry, 34 models × 4 configs | extracted from spreadsheet |
| `units.py` | unit conversions (UoMi/UoMo) | Module4 |
| `validation.py` | input validation layer | new (physics + fit-range limits) |
| `types.py` | WCACInputs / WCACResult dataclasses | new |
| `calculate.py` | `calculate()` orchestration | calc sheet wiring |

## Running each target

```bash
# Library (any Python)
python -c "from wcac import calculate, WCACInputs; print(calculate(WCACInputs()).Q_Btu_h)"

# CLI
python -m targets.cli.wcac_cli --reference
python -m targets.cli.wcac_cli --model W0490 --tube-temp 300 --datasheet out.txt

# Desktop GUI
python -m targets.desktop.wcac_gui

# REST API
pip install -r targets/api/requirements.txt
uvicorn targets.api.main:app --port 8000        # docs at http://localhost:8000/docs

# Web (richer, API-backed)
#   serve targets/web/index.html; set window.WCAC_API to the API URL

# Android
#   open targets/android in Android Studio; set BASE_URL in WcacApi.kt
```

## Validation & testing

```bash
# Validate against the ORIGINAL spreadsheet (needs Excel + xlwings)
python -m tests.spreadsheet.compare           # 73 scenarios, 984 comparisons (~99.3%)
python -m tests.spreadsheet.compare --quick   # 6-scenario subset

# Independent fluid-property checks (NIST / Incropera / IAPWS-IF97)
python tests/reference_data/fluid_properties.py

# Input-validation audit (what should be rejected/warned)
python tests/reference_data/validation_cases.py

# Re-extract exact geometry from the spreadsheet (if the .xlsm changes)
python -m tests.spreadsheet.extract_geometry
```

See `formulas.md`, `CALCULATION_DISCREPANCIES.md`, and `KNOWN_LIMITATIONS.md`
for the engineering detail behind the numbers.

## Deployment notes

- **API**: containerize `targets/api` (FastAPI + uvicorn). Swap SQLite for
  PostgreSQL by changing the connection in `db.py`. Serve behind HTTPS.
- **Web**: static `index.html` on any CDN; set `WCAC_API` to the API origin.
- **Desktop**: `pyinstaller --onefile --windowed targets/desktop/wcac_gui.py`
  produces a standalone `.exe` / `.app` (engine ships inside, for trusted local use).
- **Android**: `./gradlew assembleRelease` → signed APK; points at the API.

## Proprietary-isolation invariant

The original contract's rule still holds, generalized: **no client that is
delivered to an untrusted device may contain the calculation formulas.**
- Web front-end (`targets/web`, `public/`): form + rendering only.
- Android (`targets/android`): form + rendering only; calls the API.
- The engine ships only to (a) the server, or (b) trusted local installs
  (CLI, desktop) that the engineer runs on their own machine.
