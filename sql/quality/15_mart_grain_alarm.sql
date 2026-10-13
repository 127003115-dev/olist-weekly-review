-- Must return zero; one row per source order.
SELECT 'grain_or_coverage_failure' AS failure
WHERE (SELECT COUNT(*) FROM mart_orders)!=(SELECT COUNT(*) FROM raw_orders)
OR (SELECT COUNT(*) FROM mart_orders)!=(SELECT COUNT(DISTINCT order_id) FROM mart_orders);
