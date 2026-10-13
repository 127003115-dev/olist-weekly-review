SELECT p.order_id FROM raw_payments p LEFT JOIN raw_orders o USING(order_id) WHERE o.order_id IS NULL;
