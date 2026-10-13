-- Stratified descriptive check: compare late and on-time within the same state/month.
WITH cells AS (SELECT customer_state,strftime('%Y-%m',purchased_at) month,
 SUM(delay_days>0) late_n,SUM(delay_days<=0) ontime_n,
 AVG(CASE WHEN delay_days>0 THEN review_score END) late_score,
 AVG(CASE WHEN delay_days<=0 THEN review_score END) ontime_score
 FROM mart_delivered_orders WHERE review_score IS NOT NULL GROUP BY 1,2),
 eligible AS (SELECT * FROM cells WHERE late_n>=20 AND ontime_n>=20)
 SELECT COUNT(*) cells,SUM(late_n) late_orders,SUM(ontime_n) ontime_orders,
 SUM(late_n*(ontime_score-late_score))/NULLIF(SUM(late_n),0) weighted_score_gap,
 SUM(ontime_score>late_score) cells_with_lower_late_score FROM eligible;
