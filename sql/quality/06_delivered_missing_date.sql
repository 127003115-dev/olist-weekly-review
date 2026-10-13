-- Delivered orders missing actual delivery timestamp
SELECT order_id FROM stg_orders WHERE order_status='delivered' AND delivered_at IS NULL;
