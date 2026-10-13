"""Small, adversarial SQL fixtures: grain, identity, gaps, ties and guardrails."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pipeline import ROOT, build

class Queries(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(':memory:')
        self.con.executescript('''
        CREATE TABLE mart_valid_orders(order_id TEXT,customer_unique_id TEXT,purchased_at TEXT,
        item_cents INT,order_status TEXT,delay_days REAL,review_score INT,payment_mismatch INT);
        CREATE VIEW mart_delivered_orders AS SELECT * FROM mart_valid_orders WHERE order_status='delivered';
        CREATE TABLE mart_order_items(customer_state TEXT,category TEXT,price_cents INT,order_id TEXT);
        ''')
    def tearDown(self): self.con.close()
    def query(self,name): return self.con.execute((ROOT/'sql/analysis'/name).read_text()).fetchall()
    def add(self,order,person,day,cents=100,status='delivered',delay=0,score=5):
        self.con.execute('INSERT INTO mart_valid_orders VALUES (?,?,?,?,?,?,?,0)',(order,person,day,cents,status,delay,score))
    def test_repeat_identity_and_cancellation(self):
        self.add('a','person','2017-01-01');self.add('b','person','2017-01-02')
        self.add('c','other','2017-01-02');self.add('d','other','2017-01-03',status='canceled')
        self.assertEqual(self.query('04_repeat_purchase.sql')[0],(2,1,50.0,3))
    def test_rolling_zero_days(self):
        self.add('a','p','2017-01-01');self.add('b','q','2017-01-07')
        rows=self.query('03_rolling_orders.sql')
        self.assertEqual(len(rows),7); self.assertIsNone(rows[0][2]);self.assertEqual(rows[6][2],0.29)
    def test_dense_rank_ties(self):
        self.con.executemany('INSERT INTO mart_order_items VALUES (?,?,?,?)',
                             [('SP',c,v,c) for c,v in [('a',500),('b',400),('c',300),('d',300),('e',200)]])
        self.assertEqual(len(self.query('02_top_categories.sql')),4)
    def test_month_gaps_and_zero_base(self):
        self.add('a','p','2017-01-01',100);self.add('b','p','2017-03-01',200)
        self.add('c','p','2017-05-01')
        rows=self.query('01_monthly_revenue.sql')
        self.assertEqual([r[1] for r in rows],[1.0,0,2.0,0]);self.assertIsNone(rows[2][-1])
    def test_delay_reviews(self):
        self.add('a','p','2017-01-01',delay=-3,score=5)
        self.add('b','q','2017-01-01',delay=2,score=1)
        groups={r[1]:r for r in self.query('05_delivery_reviews.sql') if r[0]=='delivery_group'}
        self.assertEqual(groups['Late'][-1],100.0);self.assertEqual(groups['On time / early'][3],-3)
    def test_missing_file_fails_preserves_database(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data') as d:
            folder=Path(d); db=folder/'published.sqlite';db.write_bytes(b'previous snapshot')
            with self.assertRaisesRegex(ValueError,'Missing required file'):
                build(folder,db,folder/'reports')
            self.assertEqual(db.read_bytes(),b'previous snapshot')
    def test_missing_column_clear_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data') as d:
            folder=Path(d)
            (folder/'olist_orders_dataset.csv').write_text('order_id\na\n')
            with self.assertRaisesRegex(ValueError,'missing expected columns'):
                build(folder,folder/'test.sqlite',folder/'reports')
    def test_mart_preaggregates_items_and_payments(self):
        con=sqlite3.connect(':memory:')
        con.executescript('''
        CREATE TABLE stg_orders(order_id TEXT,customer_id TEXT,order_status TEXT,purchased_at TEXT,
        delivered_at TEXT,estimated_at TEXT);
        INSERT INTO stg_orders VALUES('o','c','delivered','2017-01-01','2017-01-02','2017-01-03');
        CREATE TABLE stg_customers(customer_id TEXT,customer_unique_id TEXT,state TEXT);
        INSERT INTO stg_customers VALUES('c','person','SP');
        CREATE TABLE stg_items(order_id TEXT,order_item_id INT,product_id TEXT,price_cents INT,freight_cents INT);
        INSERT INTO stg_items VALUES('o',1,'p',1000,100),('o',2,'p',2000,200);
        CREATE TABLE stg_payments(order_id TEXT,value_cents INT);
        INSERT INTO stg_payments VALUES('o',2000),('o',1300);
        CREATE TABLE stg_reviews(order_id TEXT,review_score INT);
        INSERT INTO stg_reviews VALUES('o',5);
        CREATE TABLE stg_products(product_id TEXT,category TEXT);
        INSERT INTO stg_products VALUES('p','test');
        ''')
        con.executescript((ROOT/'sql/marts.sql').read_text())
        self.assertEqual(con.execute('SELECT item_cents,freight_cents,payment_cents FROM mart_orders').fetchall(),[(3000,300,3300)])
        self.assertEqual(con.execute('SELECT SUM(price_cents) FROM mart_order_items').fetchone()[0],3000)
        con.close()

if __name__=='__main__': unittest.main()
