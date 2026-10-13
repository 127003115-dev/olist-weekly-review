-- Aggregate each one-to-many relationship BEFORE joining to orders.
CREATE TABLE mart_orders AS WITH items AS (
 SELECT order_id,COUNT(*) item_count,SUM(price_cents) item_cents,SUM(freight_cents) freight_cents
 FROM stg_items GROUP BY order_id), payments AS (
 SELECT order_id,COUNT(*) payment_count,SUM(value_cents) payment_cents
 FROM stg_payments GROUP BY order_id)
 SELECT o.*,c.customer_unique_id,c.state customer_state,
 COALESCE(i.item_count,0) item_count,COALESCE(i.item_cents,0) item_cents,
 COALESCE(i.freight_cents,0) freight_cents,COALESCE(p.payment_count,0) payment_count,
 COALESCE(p.payment_cents,0) payment_cents,r.review_score,
 CASE WHEN o.delivered_at IS NOT NULL THEN julianday(date(o.delivered_at))-julianday(date(o.estimated_at)) END delay_days,
 CASE WHEN o.delivered_at IS NOT NULL THEN julianday(o.delivered_at)-julianday(o.purchased_at) END delivery_days,
 CASE WHEN o.delivered_at<o.purchased_at OR (o.order_status='delivered' AND o.delivered_at IS NULL) THEN 1 ELSE 0 END quarantined,
 CASE WHEN COALESCE(i.item_count,0)>0 AND ABS(COALESCE(p.payment_cents,0)-i.item_cents-i.freight_cents)>100 THEN 1 ELSE 0 END payment_mismatch
 FROM stg_orders o JOIN stg_customers c USING(customer_id)
 LEFT JOIN items i USING(order_id) LEFT JOIN payments p USING(order_id)
 LEFT JOIN stg_reviews r USING(order_id);
CREATE UNIQUE INDEX ix_mart_orders ON mart_orders(order_id);
CREATE VIEW mart_valid_orders AS SELECT * FROM mart_orders WHERE quarantined=0;
CREATE VIEW mart_delivered_orders AS SELECT * FROM mart_valid_orders WHERE order_status='delivered';
CREATE TABLE mart_order_items AS SELECT i.*,p.category,o.customer_state,o.purchased_at
 FROM stg_items i JOIN stg_products p USING(product_id)
 JOIN mart_delivered_orders o USING(order_id);
