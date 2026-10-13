-- Delivered merchandise GMV, excluding freight; grouped by purchase month.
-- Completed calendar months through the final month with delivered purchases.
-- Sep/Oct 2018 contain trailing non-delivered orders, not comparable growth.
WITH RECURSIVE bounds AS (
 SELECT date(MIN(purchased_at),'start of month') first_month,
 MIN(date(MAX(purchased_at),'start of month','-1 month'),
     date((SELECT MAX(purchased_at) FROM mart_delivered_orders),'start of month')) last_month
 FROM mart_valid_orders),
 months(month) AS (SELECT first_month FROM bounds UNION ALL
 SELECT date(month,'+1 month') FROM months,bounds WHERE month<last_month),
 revenue AS (SELECT date(purchased_at,'start of month') month,SUM(item_cents)/100.0 revenue_brl,
 COUNT(*) orders FROM mart_delivered_orders GROUP BY 1),
 calendar AS (SELECT m.month,COALESCE(r.revenue_brl,0) revenue_brl,COALESCE(r.orders,0) orders
 FROM months m LEFT JOIN revenue r USING(month)),
 lagged AS (SELECT *,LAG(revenue_brl) OVER(ORDER BY month) previous_revenue_brl FROM calendar)
 SELECT *,ROUND(100.0*(revenue_brl-previous_revenue_brl)/NULLIF(previous_revenue_brl,0),2) growth_pct
 FROM lagged ORDER BY month;
