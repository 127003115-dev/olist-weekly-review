-- Customers with missing identity or duplicate keys
SELECT customer_id, COUNT(*) AS occurrences FROM raw_customers GROUP BY customer_id HAVING customer_id IS NULL OR TRIM(customer_id)='' OR COUNT(*)>1 OR SUM(customer_unique_id IS NULL OR TRIM(customer_unique_id)='')>0;
