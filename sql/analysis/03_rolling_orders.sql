-- All valid placed orders including canceled orders; zero days included.
WITH RECURSIVE bounds AS (SELECT date(MIN(purchased_at)) start_day,date(MAX(purchased_at)) end_day
 FROM mart_valid_orders), days(day) AS (SELECT start_day FROM bounds UNION ALL
 SELECT date(day,'+1 day') FROM days,bounds WHERE day<end_day),
 counts AS (SELECT date(purchased_at) day,COUNT(*) order_count FROM mart_valid_orders GROUP BY 1),
 calendar AS (SELECT d.day,COALESCE(c.order_count,0) order_count FROM days d LEFT JOIN counts c USING(day))
 SELECT day,order_count,CASE WHEN COUNT(*) OVER(ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)=7
 THEN ROUND(AVG(order_count) OVER(ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),2)
 END rolling_7day_average FROM calendar ORDER BY day;
