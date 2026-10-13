# Olist Weekly Business Review

A reproducible Python/SQLite ELT pipeline and five-page business review of the
Brazilian E-Commerce Public Dataset by Olist. No pandas is used for SQL analysis.

**Finding:** among valid delivered orders with reviews, late deliveries have a
62.42% score-1/2 rate versus 9.27% for on-time/early deliveries. Mean review scores
are 2.27 and 4.29 respectively. A controlled delivery exception-desk pilot is
recommended; these historical associations do not prove causality.

## Quick start in VS Code (Windows)

Prerequisite: Python **3.12**, VS Code, and the Olist dataset ZIP from
[Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
SQLite is included with Python; no database server or Kaggle API token is needed.

1. Open this folder (`olist-weekly-review`) in VS Code: **File > Open Folder**.
2. Open **Terminal > New Terminal** in the project root.
3. Create a virtual environment and install report dependencies:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Extract all nine CSVs directly into `data/raw/`. For your supplied ZIP:

   ```powershell
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\archive (1).zip" -DestinationPath data/raw -Force
   ```

5. Review the source anomalies listed below, then run the documented source policy:

   ```powershell
   .\.venv\Scripts\python.exe src/pipeline.py --apply-source-policy
   .\.venv\Scripts\python.exe src/analyze.py
   .\.venv\Scripts\python.exe src/report.py
   ```

6. Open `reports/weekly_business_review.pdf`. The report is exactly five pages.
   Query outputs are in `reports/results/`; quality counts are in
   `reports/quality.csv` and `reports/quality.json`.

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` in place of the
Windows Python paths. Dataset extraction can be done with any ZIP utility.
The pipeline and SQL exports use only the Python standard library; dependencies
in `requirements.txt` are needed for charts/PDF generation.

## Quality alarms: strict by default

```powershell
.\.venv\Scripts\python.exe src/pipeline.py
```

This **intentionally exits with status 1 on the original Olist snapshot**, reporting
known anomalies. Every check with nonzero results is an alarm in strict mode.
`--apply-source-policy` is an explicit, reviewed alternative, not a silent bypass:
it permits only checks classified as `flag` or `quarantine` in
`sql/quality/checks.json`. All structural and clean-layer checks still alarm.
Never use that switch blindly on a new dataset; inspect the audit first.

| Source finding | Failing rows | Treatment |
|---|---:|---|
| Null/duplicate order ID | 0 | Abort if present |
| Missing/duplicate customer identity | 0 | Abort if present |
| Order without customer | 0 | Abort if present |
| Delivery before purchase | 0 | Quarantine if present |
| Payment differs from item price + freight by > BRL 1 | 250 | Flag; retain original amounts |
| Delivered order without actual delivery date | 8 | Quarantine from valid metric views |
| Invalid review score | 0 | Abort if present |
| Duplicate item key | 0 | Abort if present |
| Item without order/product/seller | 0 | Abort if present |
| Delivered order without payment | 1 | Flag; merchandise GMV still uses item prices |
| Delivered order without review | 646 | Retain; omit from review-only denominator |
| Missing/unparseable mandatory timestamp | 0 | Abort if present |
| Negative/missing monetary amount | 0 | Abort if present |

Dimension keys, payment keys and payment-order relationships also pass.
The mart-grain check and post-quarantine delivery check must both return zero.
All checks are SQL files under `sql/quality/`. Each returns offending records
(duplicate-key checks return offending key groups); the Python runner counts them.
Strict mode evaluates nonstructural checks together so the alarm includes all
observed failures. Structural errors halt before building joins/indexes.

No raw orders are dropped. Eight distinct orders are quarantined, preserving
99,441 rows in `mart_orders` and leaving 96,470 valid delivered orders.
The 99,224 raw review rows yield 98,673 canonical order reviews: 551 extra rows
are collapsed. Latest answer timestamp wins, then creation timestamp, review ID,
then stable source row order. This is a declared analytical choice, not a claim
that repeated reviews are necessarily errors. Raw rows remain available.

BRL 1.00 is a reconciliation tolerance, not exact accounting equality. Split
payments are summed before comparison. Mismatches are flagged, not rewritten;
the dataset cannot establish their cause. Missing reviews are not imputed.
Audit CSV/JSON describes the **last attempted run**; `audit_quality` inside the
published database describes the published snapshot if a later run fails.

## Architecture and grains

```text
9 CSVs -> raw_* (text, source rows preserved)
       -> structural alarms
       -> stg_* (timestamps, cents, canonical reviews, ZIP aggregation)
       -> mart_orders (one row per order; audit flags)
          -> mart_valid_orders (nonquarantined)
          -> mart_delivered_orders (valid delivered)
          -> mart_order_items (one row per delivered order item)
       -> quality gates -> atomic database publication
       -> SQL result CSVs -> four charts -> five-page PDF
```

Raw/staging includes orders, items, payments, reviews, customers, sellers,
products, geolocation and category translation. ZIP prefixes stay text to retain
leading zeros. Geolocation is aggregated to one row per ZIP before any optional
use; the analysis does not need a geolocation join. Product categories use
English translations with Portuguese/unknown fallbacks.

Items and payments are independently aggregated to order grain **before** joining.
Reviews are reduced to one per order. Money is stored as integer cents, with
two-decimal source values validated before staging. The SQLite ROUND conversion
avoids float-valued money in the mart. Indices support the order joins.

The pipeline builds a fresh temporary database, checks it, closes it and atomically
replaces `data/olist.sqlite`. It never appends raw rows. On any failure, the previous
database stays intact and the temporary database is removed. Logs include each
load, transformation and SQL check; missing files/columns show the exact filename
and missing columns. Do not run two writers concurrently on the same database.
Full snapshot rebuilds suit this static assignment; distributed ingestion and
incremental CDC would be needed for a much larger changing marketplace.

## Part C: SQL-only answers

| Question | SQL | Result |
|---|---|---|
| Monthly revenue and growth | `01_monthly_revenue.sql` | Calendar CTE + LAG; delivered merchandise GMV, freight excluded |
| Top 3 categories per customer state | `02_top_categories.sql` | DENSE_RANK; includes ties at rank 3 |
| 7-day average daily order count | `03_rolling_orders.sql` | Zero-day calendar + ROWS window; first 6 days NULL |
| Repeat purchase rate | `04_repeat_purchase.sql` | 2,801 / 93,350 customers = 3.001% |
| Delay versus reviews | `05_delivery_reviews.sql` | Delivered calendar date minus estimate; breakdown by lateness and score |

All five files are in `sql/analysis/`. Additional SQL implements weekly metric
cohorts, delay buckets and a state/month descriptive robustness comparison.
`analyze.py` only executes SQL and writes its returned rows with `csv`; it does
not compute Part C in Python. `report.py` formats SQL results and plots them.

Revenue here means **delivered merchandise GMV**, not marketplace fees/net revenue.
It is assigned to purchase month using final delivery status. The dataset does
not contain commissions or returns. Interior zero months are retained; undefined
growth from a zero base is NULL. The final source month and months after the
last delivered-purchase month are excluded from comparable monthly revenue;
August 2018 is still vulnerable to extract-end fulfillment censoring.
Rolling order count includes valid placed orders of all statuses, including
cancellations; it intentionally measures demand differently from fulfilled GMV.

[Olist's customer documentation](https://www.kaggle.com/olistbr/brazilian-ecommerce/metadata)
identifies `customer_unique_id` as the repurchase identity. `customer_id` is the
order-specific customer reference, so using it would undercount repeat buyers.
The rate uses valid delivered purchases and unequal observed follow-up, not
lifetime retention. Delivery lateness uses calendar days, so delivery at any time
on the promised date is on time. Review comparisons use only reviewed deliveries.

## Metrics and report

North Star: **weekly on-time fulfilled orders**, grouped by Monday purchase week.
Supporting metrics: on-time delivery rate, low-review rate, delivered merchandise
GMV, failed-order rate. Exact numerators, denominators and rationale appear on
page 1 of the PDF; `06_weekly_metrics.sql` implements them. NULL is returned for
zero denominators. Historical final outcomes are not point-in-time snapshots.
For a live WBR, monitor mature cohorts (proposed 45 days), review coverage,
quarantine and payment flags alongside metrics.

The report contains four labelled charts, quality findings, results from all five
questions, metric definitions and a one-page VP memo. It distinguishes historical
association from causal impact and explains end-of-window and review-selection
limitations. Pilot targets/cost caps are proposed business decisions, not estimates
learned from this dataset.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/verify_idempotency.py
```

The fixture tests cover joins with multiple items/payments, repeat identity,
category ties, calendar gaps, zero-base growth, delivery-review calculations,
missing files/columns, duplicate IDs, orphan customers, invalid review scores,
strict quality alarms and preserving the old database on failure. The full-data
idempotency check rebuilds once after the initial successful run, compares SHA-256
of the complete SQLite files and writes `reports/idempotency.json`.
Full-source checks and report generation were executed on the supplied ZIP.
The optional Airflow scheduler has not been executed in a running Airflow service.

## Optional bonus: daily Airflow DAG

`dags/olist_daily.py` schedules ingestion and SQL export at **02:00 UTC daily**
(07:30 India time), with catchup off and one active run. Failures mark the task
failed in Airflow. Use Linux/WSL/Docker and a separate Python 3.12 environment;
the core project does not require Airflow. The historical snapshot will not gain
new orders by scheduling it daily.

Example setup in a Linux/WSL terminal, following
[Airflow's installation guidance](https://airflow.apache.org/docs/apache-airflow/2.10.5/installation/installing-from-pypi.html):

```bash
python3.12 -m venv .airflow-venv
source .airflow-venv/bin/activate
pip install -r requirements-airflow.txt --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt
export AIRFLOW_HOME="$PWD/.airflow"
export OLIST_PROJECT_DIR="$PWD"
mkdir -p "$AIRFLOW_HOME/dags"
cp dags/olist_daily.py "$AIRFLOW_HOME/dags/"
airflow standalone
```

Unpause `olist_weekly_review` in the Airflow UI. Run `airflow dags test
olist_weekly_review 2024-01-02` for an end-to-end scheduler check. Worker processes
must inherit `OLIST_PROJECT_DIR` and have read/write access to the project.
The DAG explicitly uses the reviewed source policy. Scheduler service tests are
left for that environment; syntax has been checked locally.

## Upload to GitHub and submit

1. In VS Code, open **Source Control**. This local workspace is already initialized;
   if you extracted the submission ZIP, select **Initialize Repository** first.
2. Stage the code, SQL, README, requirements, tests, DAG and reports. The provided
   `.gitignore` excludes the large raw CSVs, SQLite database, environments and logs.
3. Enter a commit message such as `Add Olist pipeline and weekly business review`.
4. Select **Publish to GitHub**, sign in, and choose the required visibility.
5. Open the repository on GitHub and verify that `reports/weekly_business_review.pdf`
   and the SQL/source files are present. Submit that repository URL and the PDF if
   your course asks for it separately. The ZIP is a convenience copy; upload its
   extracted contents, not just the ZIP file.

## Viva notes and attribution

Read `docs/viva_notes.md` before submitting. Be ready to explain how you prevent
join fan-out, why customer_unique_id matters, how alarms differ from reviewed
source policy, what the revenue definition excludes, and why a pilot is needed.
This implementation and analysis were created with AI assistance for this
assignment. No public notebook code was used. Follow your course's rules on
disclosing assistance and adapt the solution after understanding it.

Data source: Olist, *Brazilian E-Commerce Public Dataset by Olist*, Kaggle,
2016-2018. Raw data is not redistributed in the submission bundle; download it
from the original source and observe its license. No license over the Olist data
is claimed by this project.
