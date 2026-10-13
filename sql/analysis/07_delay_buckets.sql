WITH bucketed AS (SELECT *,CASE WHEN delay_days<=0 THEN 0 WHEN delay_days<=3 THEN 1
 WHEN delay_days<=7 THEN 2 ELSE 3 END bucket FROM mart_delivered_orders WHERE review_score IS NOT NULL)
 SELECT bucket,CASE bucket WHEN 0 THEN 'On time / early' WHEN 1 THEN '1-3 days late'
 WHEN 2 THEN '4-7 days late' ELSE '8+ days late' END label,COUNT(*) orders,
 AVG(review_score) avg_review_score,100.0*SUM(review_score<=2)/COUNT(*) low_review_pct
 FROM bucketed GROUP BY bucket ORDER BY bucket;
