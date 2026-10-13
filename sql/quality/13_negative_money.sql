-- Negative or missing item/payment money
SELECT order_id FROM stg_items WHERE price_cents IS NULL OR freight_cents IS NULL OR price_cents<0 OR freight_cents<0 UNION ALL SELECT order_id FROM stg_payments WHERE value_cents IS NULL OR value_cents<0;
