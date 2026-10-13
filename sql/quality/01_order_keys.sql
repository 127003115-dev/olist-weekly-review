-- Orders with null or duplicate IDs
SELECT order_id, COUNT(*) AS occurrences FROM raw_orders GROUP BY order_id HAVING order_id IS NULL OR TRIM(order_id)='' OR COUNT(*)>1;
