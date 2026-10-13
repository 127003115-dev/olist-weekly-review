-- Items without order, product or seller
SELECT i.order_id,i.order_item_id FROM raw_items i LEFT JOIN raw_orders o ON i.order_id=o.order_id LEFT JOIN raw_products p ON p.product_id=i.product_id LEFT JOIN raw_sellers s ON s.seller_id=i.seller_id WHERE o.order_id IS NULL OR p.product_id IS NULL OR s.seller_id IS NULL;
