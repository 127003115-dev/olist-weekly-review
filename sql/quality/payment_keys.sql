SELECT order_id,payment_sequential FROM raw_payments GROUP BY 1,2
HAVING COUNT(*)>1 OR order_id IS NULL OR payment_sequential IS NULL;
