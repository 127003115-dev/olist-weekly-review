SELECT seller_id FROM raw_sellers GROUP BY seller_id HAVING seller_id IS NULL OR COUNT(*)>1;
