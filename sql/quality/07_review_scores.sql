-- Reviews outside the integer 1-5 range
SELECT review_id, order_id FROM raw_reviews WHERE review_score IS NULL OR review_score NOT IN ('1','2','3','4','5');
