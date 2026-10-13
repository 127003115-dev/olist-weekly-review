SELECT product_category_name FROM raw_translation GROUP BY product_category_name HAVING product_category_name IS NULL OR COUNT(*)>1;
