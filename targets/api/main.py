"""
WCAC REST API — FastAPI service exposing the calculation engine.

The proprietary physics (wcac library) runs SERVER-SIDE only and is never
shipped to clients. Web front-ends and the Android app both consume this API.

Run locally:
    pip install fastapi uvicorn
    uvicorn targets.api.main:app --reload --port 8000

Endpoints:
    GET  /                 health + version
    GET  /models           list valid model codes
    GET  /fluids           list valid tube/shell fluids and flow units
    POST /validate         validate inputs, return issues (no calculation)
    POST /calculate        validate + calculate, return full result
    GET  /reference        run the W0230 reference case
    GET  /docs             interactive OpenAPI docs (auto-generated)
"""
import os
import sys
from dataclasses import asdict, fields
from typing import Optional, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from wcac import (calculate, validate, WCACInputs, WCACResult,
                  list_models, Severity, __version__ as wcac_version)
from wcac.calculate import _FLUID_CODE, TUBE_MAT_K
from wcac.units import _SCFM_DENSITY_BARA  # noqa: just to confirm import path


app = FastAPI(
    title='DMI IPAC / WCAC Heat Exchanger API',
    description='Performance calculation for DMI Air Cooled IP Heat Exchangers. '
                'Proprietary engineering engine runs server-side.',
    version=wcac_version,
)

# CORS: allow the web/mobile front-ends to call from any origin.
# Tighten allow_origins to the deployed front-end domains in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['*'],
)


# ── Pydantic request/response models (mirror the dataclasses) ─────────────────

class InputsModel(BaseModel):
    model:                     str   = 'W0230'
    bundle_type:               str   = 'Fixed'
    tube_type:                 str   = 'Std groove'
    tube_material:             str   = 'Stainless (S3040*)'
    tube_design_pressure_psig: float = 300
    tube_fluid:                str   = 'Air'
    tube_pressure_psig:        float = 150
    tube_temp_in_F:            float = 250
    tube_flow:                 float = 1423
    tube_flow_uom:             str   = 'Scfm'
    tube_fouling:              float = 0.0
    shell_fluid:               str   = 'Water'
    shell_temp_in_F:           float = 70
    shell_flow:                float = 60
    shell_flow_uom:            str   = 'USgpm'
    shell_fouling:             float = 0.0
    glycol_concentration:      float = 40
    suction_pressure_psia:     float = 14.7
    suction_temp_F:            float = 85
    suction_rh_pct:            float = 36
    surface_area_margin:       float = 0.0

    def to_inputs(self) -> WCACInputs:
        valid = {f.name for f in fields(WCACInputs)}
        return WCACInputs(**{k: v for k, v in self.model_dump().items() if k in valid})


class IssueModel(BaseModel):
    severity: str
    field:    str
    message:  str


class ValidateResponse(BaseModel):
    valid:    bool
    errors:   List[IssueModel]
    warnings: List[IssueModel]


class CalculateResponse(BaseModel):
    result:   dict
    warnings: List[IssueModel]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_issues(inp: WCACInputs):
    issues = validate(inp)
    errors = [IssueModel(severity='error', field=i.field, message=i.message)
              for i in issues if i.severity is Severity.ERROR]
    warnings = [IssueModel(severity='warning', field=i.field, message=i.message)
                for i in issues if i.severity is Severity.WARNING]
    return errors, warnings


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get('/')
def health():
    return {'ok': True, 'service': 'wcac-api', 'wcac_version': wcac_version}


@app.get('/models')
def models():
    return {'models': list_models()}


@app.get('/fluids')
def fluids():
    gases = [k for k, v in _FLUID_CODE.items() if v.startswith('g')]
    liquids = [k for k, v in _FLUID_CODE.items() if v.startswith('l')]
    return {
        'tube_fluids': gases,
        'shell_fluids': liquids,
        'tube_materials': list(TUBE_MAT_K.keys()),
        'tube_flow_uoms': ['Scfm', 'Acfm', 'lb/s', 'lb/min', 'lb/h',
                           'kg/s', 'kg/min', 'kg/h', 'Nm3/h', 'Am3/h'],
        'shell_flow_uoms': ['USgpm', 'litre/min', 'm3/h', 'm3/s',
                            'lb/s', 'lb/min', 'lb/h', 'kg/s', 'kg/min', 'kg/h'],
        'bundle_types': ['Fixed', 'Removable'],
        'tube_types': ['Std groove', 'Plain'],
    }


@app.post('/validate', response_model=ValidateResponse)
def validate_endpoint(inputs: InputsModel):
    inp = inputs.to_inputs()
    errors, warnings = _split_issues(inp)
    return ValidateResponse(valid=len(errors) == 0, errors=errors, warnings=warnings)


@app.post('/calculate', response_model=CalculateResponse)
def calculate_endpoint(inputs: InputsModel):
    inp = inputs.to_inputs()
    errors, warnings = _split_issues(inp)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={'message': 'invalid inputs',
                    'errors': [e.model_dump() for e in errors]})
    result = calculate(inp)
    return CalculateResponse(result=asdict(result), warnings=warnings)


@app.get('/reference')
def reference():
    inp = WCACInputs()
    result = calculate(inp)
    return {'inputs': asdict(inp), 'result': asdict(result)}
