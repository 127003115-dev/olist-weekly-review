SELECT product_id FROM raw_products GROUP BY product_id HAVING product_id IS NULL OR COUNT(*)>1;
