-- Delivered orders with no payment record
SELECT order_id FROM mart_orders WHERE order_status='delivered' AND payment_count=0;
