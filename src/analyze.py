"""Execute every analysis SQL file and save exact query results as CSV."""
import argparse
import csv
from pathlib import Path
import sqlite3
from pipeline import ROOT

def analyze(db=ROOT/'data/olist.sqlite',out=ROOT/'reports/results'):
    db,out=Path(db),Path(out)
    if not db.is_file(): raise FileNotFoundError(f'Run the pipeline first: missing {db}')
    out.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(f'{db.resolve().as_uri()}?mode=ro',uri=True)
    try:
        for path in sorted((ROOT/'sql/analysis').glob('*.sql')):
            result=con.execute(path.read_text())
            with (out/(path.stem+'.csv')).open('w',newline='',encoding='utf-8') as f:
                writer=csv.writer(f); writer.writerow([c[0] for c in result.description]);writer.writerows(result)
            print(f'Saved {path.stem}.csv')
    finally: con.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=ROOT/'data/olist.sqlite');args=p.parse_args()
    analyze(args.db)
