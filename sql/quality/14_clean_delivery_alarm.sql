-- Must return zero after quarantine; any remaining row stops publication.
SELECT order_id FROM mart_delivered_orders WHERE delivered_at IS NULL OR delivered_at<purchased_at;
