-- customer_id is order-specific. customer_unique_id identifies a person.
-- Completed purchases only; observed-window rate, not lifetime retention.
WITH customers AS (SELECT customer_unique_id,COUNT(*) completed_orders
 FROM mart_delivered_orders GROUP BY customer_unique_id)
 SELECT COUNT(*) customers,SUM(completed_orders>=2) repeat_customers,
 ROUND(100.0*SUM(completed_orders>=2)/NULLIF(COUNT(*),0),3) repeat_purchase_pct,
 SUM(completed_orders) completed_orders FROM customers;
