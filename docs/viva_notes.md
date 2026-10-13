# Viva preparation

1. **Why SQLite?** It is included with Python, needs no server and supports CTEs
   and window functions. The snapshot fits locally. At larger scale, use a
   warehouse, incremental loads and managed orchestration with the same grains.
2. **What makes it ELT?** Load the original CSV fields as raw text first; transform
   inside SQL into staging and marts. Preserve source data for investigation.
3. **Why is it idempotent?** Each run builds a fresh database instead of appending.
   The second full run produced the same database checksum. Failure cannot replace
   the previous published snapshot.
4. **How can joins overstate revenue?** Two items joined to two payments produce
   four rows. Summing items after that join doubles their value. Aggregate each
   relation to order grain before joining; reviews also need one row per order.
5. **Why customer_unique_id?** It links the same person across order-specific
   customer_id values. A repeat buyer has two or more valid completed orders.
6. **Why calendar rows before a rolling average?** Seven observed rows can cover
   more than seven days if zero-order days are missing. Fill the date calendar,
   then average the current day and previous six days. First six outputs are NULL.
7. **Why DENSE_RANK?** Ties share a rank without gaps. Top three ranks can contain
   more than three categories. ROW_NUMBER would arbitrarily discard ties.
8. **What does revenue mean?** Delivered merchandise GMV in BRL, excluding freight.
   It is not platform net revenue; commission/return data is unavailable.
9. **What do negative delays mean?** Delivery earlier than the promised calendar
   date. Positive means late. The overall average is negative despite meaningful
   dissatisfaction in the late minority; subgroup analysis matters.
10. **Why not drop payment mismatches?** They may reflect business adjustments or
    source issues that cannot be diagnosed here. Keep the source, flag them and
    use item prices for GMV. BRL 1 is an explicit tolerance, not an accounting fix.
11. **How do alarms work?** SQL returns violating rows. Strict mode exits nonzero
    on any violation. The explicitly chosen source policy allows documented flags
    and quarantine only; broken keys or residual clean-layer failures still stop.
12. **Why canonical reviews?** Multiple records can exist per order. Choose the
    latest answer deterministically and preserve raw rows. State the choice since
    a different review policy can change the comparison.
13. **Does lateness cause low scores?** This snapshot shows a strong association.
    Difficult shipments/product issues may affect both. A randomized operations
    pilot provides a stronger basis for decisions than correlation alone.
14. **What limits the WBR?** Final outcomes, optional reviews, short/unequal repeat
    observation, trailing incomplete months, no tracking history or fees. Mature
    cohorts and live tracking would be required for operational production use.

Before submitting, run the project yourself, inspect the CSVs and explain a query
in your own words. Disclose AI assistance according to your course requirements.
