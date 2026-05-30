"""
db — lightweight SQLite persistence for saved WCAC designs.

Stores each design's inputs, computed results, and metadata so engineers can
save, retrieve, list, and compare design cases. Uses stdlib sqlite3 (no extra
dependency). For a multi-user production deployment, swap the connection for
PostgreSQL — the schema and queries are standard SQL.
"""
import os
import json
import sqlite3
import datetime
from contextlib import contextmanager

DB_PATH = os.environ.get('WCAC_DB', os.path.join(os.path.dirname(__file__), 'wcac_designs.db'))


SCHEMA = """
CREATE TABLE IF NOT EXISTS designs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    tag         TEXT,
    model       TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    results_json TEXT NOT NULL,
    q_btu_h     REAL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_designs_model ON designs(model);
CREATE INDEX IF NOT EXISTS idx_designs_tag   ON designs(tag);
"""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript(SCHEMA)


def save_design(name, inputs: dict, results: dict, tag=None) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO designs
               (name, tag, model, inputs_json, results_json, q_btu_h, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, tag, inputs.get('model'),
             json.dumps(inputs), json.dumps(results),
             results.get('Q_Btu_h'), _now(), _now()))
        return cur.lastrowid


def list_designs(model=None, tag=None, limit=100) -> list:
    init_db()
    q = "SELECT id, name, tag, model, q_btu_h, created_at, updated_at FROM designs"
    params = []
    conds = []
    if model: conds.append('model = ?'); params.append(model)
    if tag:   conds.append('tag = ?');   params.append(tag)
    if conds: q += ' WHERE ' + ' AND '.join(conds)
    q += ' ORDER BY updated_at DESC LIMIT ?'; params.append(limit)
    with _conn() as con:
        return [dict(r) for r in con.execute(q, params).fetchall()]


def get_design(design_id: int) -> dict:
    init_db()
    with _conn() as con:
        row = con.execute('SELECT * FROM designs WHERE id = ?', (design_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d['inputs'] = json.loads(d.pop('inputs_json'))
        d['results'] = json.loads(d.pop('results_json'))
        return d


def update_design(design_id: int, name=None, tag=None,
                  inputs: dict = None, results: dict = None) -> bool:
    init_db()
    fields = []; params = []
    if name is not None:    fields.append('name = ?');         params.append(name)
    if tag is not None:     fields.append('tag = ?');          params.append(tag)
    if inputs is not None:
        fields.append('inputs_json = ?');  params.append(json.dumps(inputs))
        fields.append('model = ?');        params.append(inputs.get('model'))
    if results is not None:
        fields.append('results_json = ?'); params.append(json.dumps(results))
        fields.append('q_btu_h = ?');      params.append(results.get('Q_Btu_h'))
    if not fields:
        return False
    fields.append('updated_at = ?'); params.append(_now())
    params.append(design_id)
    with _conn() as con:
        cur = con.execute(f"UPDATE designs SET {', '.join(fields)} WHERE id = ?", params)
        return cur.rowcount > 0


def delete_design(design_id: int) -> bool:
    init_db()
    with _conn() as con:
        cur = con.execute('DELETE FROM designs WHERE id = ?', (design_id,))
        return cur.rowcount > 0
