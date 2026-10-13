"""End-to-end synthetic CSV tests prove alarms and reviewed anomaly handling."""
import csv
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pipeline import ROOT,FILES,build

class PipelineAlarms(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'data')
        self.folder=Path(self.temp.name)
        self.schema=json.loads((ROOT/'src/schema.json').read_text())
        self.rows={
            'orders':[{'order_id':'o','customer_id':'c','order_status':'delivered',
                       'order_purchase_timestamp':'2017-01-01 10:00:00',
                       'order_delivered_customer_date':'2017-01-02 12:00:00',
                       'order_estimated_delivery_date':'2017-01-03 00:00:00'}],
            'customers':[{'customer_id':'c','customer_unique_id':'person','customer_state':'SP','customer_city':'City'}],
            'items':[{'order_id':'o','order_item_id':'1','product_id':'p','seller_id':'s','price':'10.00','freight_value':'1.00'}],
            'payments':[{'order_id':'o','payment_sequential':'1','payment_value':'11.00'}],
            'reviews':[{'order_id':'o','review_id':'r','review_score':'5'}],
            'products':[{'product_id':'p','product_category_name':'test'}],
            'sellers':[{'seller_id':'s','seller_city':'City','seller_state':'SP'}],
            'translation':[{'product_category_name':'test','product_category_name_english':'test'}],
            'geolocation':[{'geolocation_zip_code_prefix':'01234','geolocation_lat':'-23','geolocation_lng':'-46'}],
        }
        self.db=self.folder/'published.sqlite'
    def tearDown(self):self.temp.cleanup()
    def run_build(self,policy=False):
        for table,filename in FILES.items():
            with (self.folder/filename).open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=self.schema[table]);w.writeheader();w.writerows(self.rows[table])
        return build(self.folder,self.db,self.folder/'reports',policy)
    def test_happy_path(self):
        self.run_build()
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('SELECT item_cents,payment_cents FROM mart_orders').fetchall(),[(1000,1100)])
    def test_duplicate_order_alarm(self):
        self.rows['orders']*=2
        with self.assertRaisesRegex(ValueError,'01_order_keys'):self.run_build(True)
        self.assertFalse(self.db.exists())
    def test_customer_relationship_alarm(self):
        self.rows['orders'][0]['customer_id']='missing'
        with self.assertRaisesRegex(ValueError,'03_orphan_customers'):self.run_build(True)
    def test_strict_payment_alarm_and_atomicity(self):
        self.run_build(); before=self.db.read_bytes()
        self.rows['payments'][0]['payment_value']='20.00'
        with self.assertRaisesRegex(ValueError,'05_payment_reconciliation'):self.run_build()
        self.assertEqual(self.db.read_bytes(),before)
    def test_policy_flags_and_quarantines(self):
        self.rows['orders'][0]['order_delivered_customer_date']=''
        self.rows['payments'][0]['payment_value']='20.00'
        self.run_build(True)
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('SELECT quarantined,payment_mismatch FROM mart_orders').fetchall(),[(1,1)])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM mart_valid_orders').fetchone()[0],0)
    def test_invalid_score_still_alarms_under_policy(self):
        self.rows['reviews'][0]['review_score']='6'
        with self.assertRaisesRegex(ValueError,'07_review_scores'):self.run_build(True)

if __name__=='__main__':unittest.main()
