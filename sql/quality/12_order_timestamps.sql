-- Missing or unparseable mandatory order timestamps
SELECT order_id FROM raw_orders WHERE julianday(order_purchase_timestamp) IS NULL OR julianday(order_estimated_delivery_date) IS NULL OR (order_delivered_customer_date IS NOT NULL AND julianday(order_delivered_customer_date) IS NULL);
