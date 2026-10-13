CREATE TABLE stg_orders AS SELECT order_id,customer_id,order_status,
 datetime(order_purchase_timestamp) purchased_at, datetime(order_approved_at) approved_at,
 datetime(order_delivered_carrier_date) carrier_at, datetime(order_delivered_customer_date) delivered_at,
 datetime(order_estimated_delivery_date) estimated_at FROM raw_orders;
CREATE UNIQUE INDEX ix_orders ON stg_orders(order_id);
CREATE TABLE stg_customers AS SELECT customer_id,customer_unique_id,customer_zip_code_prefix,
 LOWER(TRIM(customer_city)) city,UPPER(TRIM(customer_state)) state FROM raw_customers;
CREATE UNIQUE INDEX ix_customers ON stg_customers(customer_id);
CREATE TABLE stg_items AS SELECT order_id,CAST(order_item_id AS INTEGER) order_item_id,product_id,seller_id,
 datetime(shipping_limit_date) shipping_limit_at, CAST(ROUND(CAST(price AS REAL)*100) AS INTEGER) price_cents,
 CAST(ROUND(CAST(freight_value AS REAL)*100) AS INTEGER) freight_cents FROM raw_items;
CREATE INDEX ix_items ON stg_items(order_id);
CREATE TABLE stg_payments AS SELECT order_id,CAST(payment_sequential AS INTEGER) payment_sequential,
 payment_type,CAST(payment_installments AS INTEGER) installments,
 CAST(ROUND(CAST(payment_value AS REAL)*100) AS INTEGER) value_cents FROM raw_payments;
CREATE INDEX ix_payments ON stg_payments(order_id);
-- One canonical review per order. Latest answer wins, then creation date,
-- review ID and source rowid for a stable, explicit tie-break on identical rows.
CREATE TABLE stg_reviews AS WITH ranked AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY review_answer_timestamp DESC,
 review_creation_date DESC,review_id DESC,rowid DESC) rn FROM raw_reviews)
 SELECT review_id,order_id,CAST(review_score AS INTEGER) review_score,
 datetime(review_creation_date) created_at,datetime(review_answer_timestamp) answered_at
 FROM ranked WHERE rn=1;
CREATE UNIQUE INDEX ix_reviews ON stg_reviews(order_id);
CREATE TABLE stg_products AS SELECT p.product_id,p.product_category_name,
 COALESCE(t.product_category_name_english,p.product_category_name,'unknown') category,
 CAST(p.product_weight_g AS REAL) weight_g FROM raw_products p
 LEFT JOIN raw_translation t USING(product_category_name);
CREATE UNIQUE INDEX ix_products ON stg_products(product_id);
CREATE TABLE stg_sellers AS SELECT seller_id,seller_zip_code_prefix,LOWER(TRIM(seller_city)) city,
 UPPER(TRIM(seller_state)) state FROM raw_sellers;
-- Geolocation has many observations per ZIP. Collapse before any optional join.
CREATE TABLE stg_geolocation AS SELECT geolocation_zip_code_prefix zip_code_prefix,
 AVG(CAST(geolocation_lat AS REAL)) latitude,AVG(CAST(geolocation_lng AS REAL)) longitude,
 COUNT(*) source_rows FROM raw_geolocation GROUP BY geolocation_zip_code_prefix;
