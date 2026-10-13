WITH revenue AS (SELECT customer_state,category,SUM(price_cents)/100.0 revenue_brl,
 COUNT(DISTINCT order_id) orders FROM mart_order_items GROUP BY 1,2),
 ranked AS (SELECT *,DENSE_RANK() OVER(PARTITION BY customer_state ORDER BY revenue_brl DESC) category_rank
 FROM revenue)
 SELECT * FROM ranked WHERE category_rank<=3 ORDER BY customer_state,category_rank,category;
-- DENSE_RANK preserves ties, so a state can have more than three rows.
