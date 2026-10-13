-- Orders without a matching customer
SELECT o.order_id FROM raw_orders o LEFT JOIN raw_customers c ON c.customer_id=o.customer_id WHERE c.customer_id IS NULL;
