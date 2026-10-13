"""Optional Airflow 2.10+ DAG. Copy into AIRFLOW_HOME/dags on Linux/WSL.

Install requirements-airflow.txt in an isolated Airflow environment.
OLIST_PROJECT_DIR must point to the extracted repository on the worker.
The reviewed snapshot policy is explicit; raw structural failures always alarm.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT=Path(os.environ.get('OLIST_PROJECT_DIR','/opt/olist-weekly-review'))

def ingest():
    sys.path.insert(0,str(PROJECT/'src'))
    from pipeline import build
    build(apply_source_policy=True)

def analyze():
    sys.path.insert(0,str(PROJECT/'src'))
    from analyze import analyze as execute
    execute()

with DAG('olist_weekly_review',start_date=datetime(2024,1,1,tzinfo=timezone.utc),
         schedule='0 2 * * *',catchup=False,max_active_runs=1,
         default_args={'owner':'analytics','retries':0},tags=['olist','quality']) as dag:
    load=PythonOperator(task_id='load_validate_publish',python_callable=ingest)
    sql=PythonOperator(task_id='export_sql_results',python_callable=analyze)
    load >> sql
