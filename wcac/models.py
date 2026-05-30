"""
wcac.models — Standard model geometry table (W0035–W5000).

Data from W1279 DMI WCAC Design program I0-1.xlsm, models sheet.
All source dimensions in inches; converted to metres on access.

Tuple layout per model:
  (shell_id_in, nozzle_id_in, tube_len_in, pitch_in, pattern,
   n_rows, otl_diam_in, nt_miss, first_row, cv_offset_in,
   baffle_dia_in, bcut_cl_in, nb_fixed, nb_removable, hole_dia_in,
   lbc_std_in,                   ← standard central baffle gap (Z column)
   ts_200psig_fixed_in,          ← tubesheet thk at 200 psig, Fixed
   ts_300psig_fixed_in,          ← tubesheet thk at 300 psig, Fixed
   ts_200psig_rem_in,            ← tubesheet thk at 200 psig, Removable
   ts_300psig_rem_in)             ← tubesheet thk at 300 psig, Removable

Geometry overrides (see CALCULATION_DISCREPANCIES.md):
  For W0230 the geometry sheet uses ts_geom=2.3125" (not ts300f=1.25")
  for Lt_eff, ts_lbe=1.25" for Lbe, and design_lbc=1.000" for Acs.
"""
from dataclasses import dataclass
from typing import Literal


PatternT = Literal['T', 'S', 'RS']


@dataclass(frozen=True)
class ModelGeometry:
    """Geometry parameters for one model, all in metres."""
    code:          str
    Dsi:           float   # shell inner diameter
    Dsn:           float   # shell nozzle inner diameter
    Lt:            float   # tube length (full, over tubesheets)
    Xt:            float   # tube pitch
    pattern:       PatternT
    N_rows:        int     # number of tube rows
    OTL:           float   # outer tube limit DIAMETER (not radius)
    Nt_miss:       int     # tubes missing from std layout
    first_row:     str     # 'land' or 'hole'
    cv_offset:     float   # centre-row lateral offset (RS pattern)
    Dbaffle:       float   # baffle outside diameter
    Bcut_cl:       float   # baffle cut distance from centreline
    Nb_fixed:      int     # baffles, Fixed bundle
    Nb_removable:  int     # baffles, Removable bundle
    Dhole:         float   # tube hole diameter in baffle
    Lbc_std:       float   # standard central baffle gap (Z column)
    ts_200f:       float   # tubesheet thk, 200 psig Fixed
    ts_300f:       float   # tubesheet thk, 300 psig Fixed
    ts_200r:       float   # tubesheet thk, 200 psig Removable
    ts_300r:       float   # tubesheet thk, 300 psig Removable


# Raw table: all dimensions in inches
_RAW = {
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
    'W0230': (5.047,1.380,59.000,0.625,'T',7,4.249,0,'land',0.000,4.875,1.082,34,34,0.516,1.313,1.250,1.250,1000,1000),
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

_I = 0.0254  # inch → metre


def get_model(code: str) -> ModelGeometry:
    """Return ModelGeometry for the given model code.  Raises ValueError if unknown."""
    row = _RAW.get(code)
    if row is None:
        raise ValueError(f"Unknown model '{code}'. Valid codes: {list(_RAW)}")
    (dsi,dsn,lt,pitch,pat,rows,otl,nt_miss,fr,cvo,
     bdiam,bcut,nb_f,nb_r,hole,lbc,ts200f,ts300f,ts200r,ts300r) = row
    return ModelGeometry(
        code=code, Dsi=dsi*_I, Dsn=dsn*_I, Lt=lt*_I, Xt=pitch*_I,
        pattern=pat, N_rows=rows, OTL=otl*_I, Nt_miss=nt_miss,
        first_row=fr, cv_offset=cvo*_I, Dbaffle=bdiam*_I, Bcut_cl=bcut*_I,
        Nb_fixed=nb_f, Nb_removable=nb_r, Dhole=hole*_I, Lbc_std=lbc*_I,
        ts_200f=ts200f*_I, ts_300f=ts300f*_I,
        ts_200r=ts200r*_I, ts_300r=ts300r*_I,
    )


def list_models() -> list:
    """Return list of all valid model codes in size order."""
    return list(_RAW.keys())


# Verified geometry overrides (geometry sheet F11, F24, F26 — see CALCULATION_DISCREPANCIES.md)
# Keys: model code.  Values: (ts_geom_m, ts_lbe_m, design_lbc_m)
#   ts_geom    = tubesheet thickness for Lt_eff (heat transfer area)
#   ts_lbe     = tubesheet thickness for Lbe formula
#   design_lbc = actual central baffle gap for Acs / flow velocity
GEOMETRY_OVERRIDES = {
    'W0230': (2.3125 * _I, 1.250 * _I, 1.000 * _I),
    # Add other verified models here as geometry sheets are cross-checked.
}
