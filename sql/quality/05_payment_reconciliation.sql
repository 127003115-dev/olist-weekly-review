-- Payment differs from items plus freight by more than BRL 1
SELECT order_id, payment_cents-item_cents-freight_cents AS difference_cents FROM mart_orders WHERE item_count>0 AND ABS(payment_cents-item_cents-freight_cents)>100;
