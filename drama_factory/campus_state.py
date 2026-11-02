"""Episode state reuses the existing SQLite store and transactional CAD cap."""
import json
from decimal import Decimal
from pathlib import Path
from .store import Store
from .film import digest

JOB = 'campus_episode_01'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Production:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.store = Store(self.root)
        with self.store.connection() as db:
            db.execute('INSERT OR IGNORE INTO jobs VALUES(?,?,?,NULL)',(JOB,'preproduction','{}'))
            db.executescript('''
            CREATE TABLE IF NOT EXISTS film_requests(id TEXT PRIMARY KEY, payload_sha TEXT NOT NULL,
              status TEXT NOT NULL, task_id TEXT, target TEXT NOT NULL, asset_sha TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS film_approvals(name TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS film_reconciliation(id TEXT PRIMARY KEY, source TEXT NOT NULL);
            ''')

    def request(self, rid):
        with self.store.connection() as db:
            row=db.execute('SELECT * FROM film_requests WHERE id=?',(rid,)).fetchone()
            return dict(row) if row else None

    def begin(self, rid, payload, amount, target):
        fingerprint=digest(payload)
        row=self.request(rid)
        if row:
            if row['payload_sha']!=fingerprint:
                raise ValueError(f'{rid}: inputs changed. Do not reuse or delete a paid request. Reconcile and explicitly plan a new approved request.')
            return row
        self.store.reserve(JOB,rid,amount)
        with self.store.connection() as db:
            db.execute('INSERT INTO film_requests VALUES(?,?,?,?,?,?,?)',(rid,fingerprint,'submitting',None,str(target),None,None))
        result=self.request(rid)
        result['_fresh']=True
        return result

    def update(self,rid,**fields):
        allowed={'status','task_id','asset_sha','error'}
        if not fields or not set(fields)<=allowed:
            raise ValueError('Invalid state update')
        with self.store.connection() as db:
            db.execute('UPDATE film_requests SET '+','.join(f'{k}=?' for k in fields)+' WHERE id=?',(*fields.values(),rid))

    def costs(self):
        with self.store.connection() as db:
            return {r['request_id']:dict(r) for r in db.execute('SELECT * FROM costs WHERE job=?',(JOB,))}

    def report(self):
        rows=self.costs()
        actual=sum(r['actual'] or 0 for r in rows.values())
        held=sum(r['reserved'] for r in rows.values() if r['actual'] is None)
        return dict(currency='CAD',cap='18.00',actual_reported_cad=f'{actual/100:.2f}',unreconciled_reserved_cad=f'{held/100:.2f}',committed_cad=f'{(actual+held)/100:.2f}',requests=rows,note='Actual charges are unknown until provider billing is reconciled. Successful API tasks do not establish billing.')

    def approve(self,name,fingerprint):
        with self.store.connection() as db:
            db.execute('INSERT INTO film_approvals VALUES(?,?) ON CONFLICT(name) DO UPDATE SET fingerprint=excluded.fingerprint',(name,fingerprint))

    def approved(self,name,fingerprint):
        with self.store.connection() as db:
            row=db.execute('SELECT fingerprint FROM film_approvals WHERE name=?',(name,)).fetchone()
            return bool(row and row[0]==fingerprint)

    def reconcile(self,rid,actual,source):
        amount=Decimal(actual)
        if not amount.is_finite() or amount<0 or amount.as_tuple().exponent < -2 or not source.strip():
            raise ValueError('Actual cost must be nonnegative CAD cents with a billing source')
        row=self.request(rid)
        if row is None or row['status'] not in ('complete','failed'):
            raise ValueError('Only completed or failed, confirmed requests can reconcile; ambiguous submissions need provider investigation')
        with self.store.connection() as db:
            db.execute('UPDATE costs SET actual=? WHERE job=? AND request_id=?',(int(amount*100),JOB,rid))
            db.execute('INSERT INTO film_reconciliation VALUES(?,?) ON CONFLICT(id) DO UPDATE SET source=excluded.source',(rid,source))
        if Decimal(self.report()['committed_cad'])>18:
            raise ValueError('Provider actual billing exceeded the cap; recorded truthfully. Stop production and investigate pricing.')
