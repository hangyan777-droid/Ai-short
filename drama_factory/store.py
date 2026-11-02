import json
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from .budget import CAP

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'campus.sqlite3'
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY, profile TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, status TEXT NOT NULL, storyboard TEXT NOT NULL, error TEXT);
            CREATE TABLE IF NOT EXISTS shots(job TEXT, idx INTEGER, status TEXT NOT NULL, review TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(job,idx));
            CREATE TABLE IF NOT EXISTS costs(job TEXT, request_id TEXT, reserved INTEGER NOT NULL, actual INTEGER, PRIMARY KEY(job,request_id));
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, job, request_id, cad):
        amount = Decimal(str(cad))
        if not amount.is_finite() or amount < 0:
            raise ValueError('Invalid reservation')
        cents = int((amount * 100).to_integral_value(rounding='ROUND_UP'))
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM jobs WHERE id=?', (job,)).fetchone():
                raise ValueError('Unknown job')
            old = db.execute('SELECT reserved FROM costs WHERE job=? AND request_id=?', (job, request_id)).fetchone()
            if old:
                if old['reserved'] != cents:
                    raise ValueError('Request already reserved at a different price')
                return
            used = db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM costs WHERE job=?', (job,)).fetchone()[0]
            if used + cents > int(CAP * 100):
                raise ValueError('CAD $18 episode limit exceeded')
            db.execute('INSERT INTO costs VALUES(?,?,?,NULL)', (job, request_id, cents))

    def job(self, job):
        with self.connection() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone()
            if row is None:
                raise KeyError(job)
            result = dict(row)
            result['storyboard'] = json.loads(result['storyboard'])
            result['shots'] = [dict(s) for s in db.execute('SELECT idx,status,review FROM shots WHERE job=? ORDER BY idx', (job,))]
            cost = db.execute('SELECT COALESCE(SUM(COALESCE(actual,0)),0), COALESCE(SUM(CASE WHEN actual IS NULL THEN reserved ELSE 0 END),0) FROM costs WHERE job=?', (job,)).fetchone()
            result['cost'] = {'actual_cad': cost[0] / 100, 'reserved_cad': cost[1] / 100, 'limit_cad': 18}
            return result
