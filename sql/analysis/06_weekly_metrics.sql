-- Monday purchase cohorts. Historical final outcomes, not point-in-time snapshots.
WITH cohorts AS (SELECT *,date(purchased_at,'-'||((CAST(strftime('%w',purchased_at) AS INTEGER)+6)%7)||' days') week_start
 FROM mart_valid_orders), weekly AS (
 SELECT week_start,COUNT(*) placed_orders,SUM(order_status='delivered') delivered_orders,
 SUM(order_status='delivered' AND delay_days<=0) on_time_delivered_orders,
 SUM(CASE WHEN order_status='delivered' THEN item_cents ELSE 0 END)/100.0 delivered_gmv_brl,
 SUM(order_status='delivered' AND review_score IS NOT NULL) reviewed_deliveries,
 SUM(order_status='delivered' AND review_score<=2) low_reviews,
 SUM(order_status IN ('canceled','unavailable')) failed_orders,
 SUM(payment_mismatch) reconciliation_flags FROM cohorts GROUP BY 1)
 SELECT *,100.0*on_time_delivered_orders/NULLIF(delivered_orders,0) on_time_pct,
 100.0*low_reviews/NULLIF(reviewed_deliveries,0) low_review_pct,
 100.0*failed_orders/NULLIF(placed_orders,0) failed_order_pct FROM weekly ORDER BY week_start;
