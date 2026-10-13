-- Calendar-day actual minus promised date: negative means early, positive late.
WITH scored AS (SELECT *,CASE WHEN delay_days>0 THEN 'Late' ELSE 'On time / early' END delivery_group
 FROM mart_delivered_orders WHERE review_score IS NOT NULL),
 grouped AS (SELECT delivery_group,COUNT(*) orders,AVG(delay_days) avg_delay_days,
 AVG(review_score) avg_review_score,100.0*SUM(review_score<=2)/COUNT(*) low_review_pct
 FROM scored GROUP BY delivery_group), by_score AS (
 SELECT CAST(review_score AS TEXT) delivery_group,COUNT(*) orders,AVG(delay_days) avg_delay_days,
 AVG(review_score) avg_review_score,100.0*SUM(review_score<=2)/COUNT(*) low_review_pct
 FROM scored GROUP BY review_score)
 SELECT 'delivery_group' breakdown,* FROM grouped UNION ALL
 SELECT 'review_score' breakdown,* FROM by_score ORDER BY breakdown,delivery_group;
