"""Idempotent CSV -> raw -> staging -> order mart with atomic publication.

SQLite 3.25+ provides the window functions used here. No pandas is used.
Quality is fail-closed by default. Reviewed Olist anomalies can be published
only with the explicit --apply-source-policy switch; structural errors still fail.
"""
from __future__ import annotations
import argparse
import csv
import json
import logging
import os
from pathlib import Path
import sqlite3
from decimal import Decimal, InvalidOperation

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger('olist')
FILES = {
    'orders':'olist_orders_dataset.csv', 'items':'olist_order_items_dataset.csv',
    'payments':'olist_order_payments_dataset.csv','reviews':'olist_order_reviews_dataset.csv',
    'customers':'olist_customers_dataset.csv','products':'olist_products_dataset.csv',
    'sellers':'olist_sellers_dataset.csv','geolocation':'olist_geolocation_dataset.csv',
    'translation':'product_category_name_translation.csv',
}

def load_raw(con, raw_dir):
    schemas=json.loads((ROOT/'src/schema.json').read_text())
    counts={}
    for table, filename in FILES.items():
        path=raw_dir/filename
        if not path.is_file():
            raise ValueError(f'Missing required file: {path}. Extract the Olist ZIP into {raw_dir}.')
        with path.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream)
            expected=schemas[table]
            missing=set(expected)-set(reader.fieldnames or [])
            if missing:
                raise ValueError(f'{filename}: missing expected columns {sorted(missing)}')
            if len(reader.fieldnames)!=len(set(reader.fieldnames)):
                raise ValueError(f'{filename}: duplicate column names')
            columns=','.join('"'+c+'" TEXT' for c in expected)
            con.execute(f'CREATE TABLE raw_{table} ({columns})')
            stmt=f'INSERT INTO raw_{table} VALUES ({",".join("?" for _ in expected)})'
            batch=[]; count=0
            for line,row in enumerate(reader,2):
                if None in row or any(row.get(c) is None for c in expected):
                    raise ValueError(f'{filename} row {line}: malformed CSV record')
                for col in ('price','freight_value','payment_value'):
                    if col in expected and row[col]:
                        try:
                            value=Decimal(row[col])
                            if not value.is_finite() or value*100!=(value*100).to_integral_value():
                                raise InvalidOperation
                        except InvalidOperation:
                            raise ValueError(f'{filename} row {line}: invalid two-decimal money in {col}') from None
                batch.append(tuple(row[c] if row[c]!='' else None for c in expected)); count+=1
                if len(batch)==10000:
                    con.executemany(stmt,batch); batch=[]
            if batch: con.executemany(stmt,batch)
        counts[table]=count
        LOG.info('Loaded raw_%s: %s rows',table,count)
    con.commit()
    return counts

def run_sql(con,path):
    LOG.info('Executing %s',path.name)
    con.executescript(path.read_text(encoding='utf-8'))

def check(con,name,metadata,phase):
    sql=(ROOT/'sql/quality'/f'{name}.sql').read_text()
    failures=con.execute(f'SELECT COUNT(*) FROM ({sql.rstrip().rstrip(";")})').fetchone()[0]
    result={'check':name,'description':metadata['label'],'phase':phase,
            'failing_rows':failures,'action':metadata['action']}
    LOG.log(logging.WARNING if failures else logging.INFO,'DQ %s: %s failing rows; action=%s',name,failures,metadata['action'])
    return result

def write_audit(results,counts,report_dir,con=None):
    report_dir.mkdir(parents=True,exist_ok=True)
    audit={'source_counts':counts,'checks':results}
    if con is not None:
        audit['review_rows_removed']=con.execute('SELECT (SELECT COUNT(*) FROM raw_reviews)-(SELECT COUNT(*) FROM stg_reviews)').fetchone()[0]
        audit['quarantined_orders']=con.execute('SELECT COUNT(*) FROM mart_orders WHERE quarantined=1').fetchone()[0]
        audit['mart_rows']=con.execute('SELECT COUNT(*) FROM mart_orders').fetchone()[0]
    (report_dir/'quality.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    with (report_dir/'quality.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['check','description','phase','failing_rows','action'])
        writer.writeheader(); writer.writerows(results)

def build(raw_dir=ROOT/'data/raw',db=ROOT/'data/olist.sqlite',report_dir=ROOT/'reports',apply_source_policy=False):
    raw_dir,db,report_dir=map(Path,(raw_dir,db,report_dir))
    db.parent.mkdir(parents=True,exist_ok=True)
    temp=db.with_suffix('.tmp.sqlite')
    if temp.exists(): temp.unlink()
    con=sqlite3.connect(temp)
    results=[]; counts={}
    metadata=json.loads((ROOT/'sql/quality/checks.json').read_text())
    try:
        counts=load_raw(con,raw_dir)
        # Key/relationship alarms must run BEFORE unique indexes and joins.
        pre=['01_order_keys','02_customer_keys','03_orphan_customers','07_review_scores',
             '08_item_keys','09_orphan_items','12_order_timestamps']
        for name in pre: results.append(check(con,name,metadata[name],'raw'))
        # Dimension keys and payment composite keys must be unique too.
        extra={'products_keys':'Invalid products keys','sellers_keys':'Invalid sellers keys',
               'translation_keys':'Invalid translation keys','payment_keys':'Invalid payment keys',
               'payment_order_fk':'Payment without order'}
        for name,label in extra.items():
            results.append(check(con,name,{'label':label,'action':'abort'},'raw'))
        if any(r['failing_rows'] for r in results):
            write_audit(results,counts,report_dir)
            raise ValueError('Raw quality ALARM: '+', '.join(r['check'] for r in results if r['failing_rows']))
        run_sql(con,ROOT/'sql/staging.sql')
        run_sql(con,ROOT/'sql/marts.sql')
        for name in metadata:
            if name not in pre: results.append(check(con,name,metadata[name],'staging/mart'))
        for name in ['14_clean_delivery_alarm','15_mart_grain_alarm']:
            results.append(check(con,name,{'label':name,'action':'abort'},'publication'))
        write_audit(results,counts,report_dir,con)
        violations=[r for r in results if r['failing_rows'] and (r['action']=='abort' or not apply_source_policy)]
        if violations:
            raise ValueError('Quality ALARM: '+', '.join(f"{r['check']}={r['failing_rows']}" for r in violations)+
                             '. See reports/quality.csv. After reviewing known source anomalies, use --apply-source-policy to flag/quarantine them.')
        con.execute('CREATE TABLE audit_quality(check_name TEXT, failing_rows INTEGER, action TEXT)')
        con.executemany('INSERT INTO audit_quality VALUES (?,?,?)',[(r['check'],r['failing_rows'],r['action']) for r in results])
        con.commit(); con.close(); con=None
        os.replace(temp,db)
        LOG.info('SUCCESS: published %s atomically; raw snapshot rebuilt without appending',db)
        return results
    except Exception:
        LOG.exception('Pipeline FAILED; previous published database remains intact')
        raise
    finally:
        if con is not None: con.close()
        if temp.exists(): temp.unlink()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    parser.add_argument('--db',type=Path,default=ROOT/'data/olist.sqlite')
    parser.add_argument('--report-dir',type=Path,default=ROOT/'reports')
    parser.add_argument('--apply-source-policy',action='store_true')
    args=parser.parse_args()
    (ROOT/'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.StreamHandler(),logging.FileHandler(ROOT/'logs/pipeline.log',encoding='utf-8')])
    try: build(args.raw_dir,args.db,args.report_dir,args.apply_source_policy)
    except Exception: raise SystemExit(1)

if __name__=='__main__': main()
