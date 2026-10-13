-- Delivery before purchase
SELECT order_id FROM stg_orders WHERE delivered_at < purchased_at;
