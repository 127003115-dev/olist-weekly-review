"""Rebuild the published snapshot once and compare every database byte.

Run after the first successful build. Deterministic input/order/SQL means the
SQLite file itself must be identical, which is stronger than checking counts.
"""
import hashlib
import json
import logging
from pipeline import ROOT, build

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    db=ROOT/'data/olist.sqlite'
    if not db.exists():raise SystemExit('Run pipeline.py --apply-source-policy first.')
    before=digest(db)
    build(apply_source_policy=True)
    after=digest(db)
    result={'test':'full snapshot rebuild','before_sha256':before,'after_sha256':after,'passed':before==after}
    (ROOT/'reports/idempotency.json').write_text(json.dumps(result,indent=2))
    if before!=after:raise SystemExit('Idempotency failed: database bytes changed.')
    print('PASS: second full run produced a byte-identical SQLite database.')
