-- Duplicate order/item composite keys
SELECT order_id, order_item_id FROM raw_items GROUP BY order_id,order_item_id HAVING COUNT(*)>1 OR order_id IS NULL OR order_item_id IS NULL;
