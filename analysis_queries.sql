USE ecommerce_dw;

-- ============================================================================
-- QUERY 1: Monthly Financial Run-Rate & Margin Trajectory
-- Business Objective: Track net revenue, COGS, and real profit margins MoM.
-- ============================================================================
SELECT 
    d.year,
    d.month_name,
    COUNT(DISTINCT f.order_id) AS completed_orders,
    ROUND(SUM(f.gross_revenue), 2) AS gross_sales,
    ROUND(SUM(f.allocated_discount), 2) AS total_discounts,
    ROUND(SUM(f.net_revenue), 2) AS net_revenue,
    ROUND(SUM(f.cogs), 2) AS total_cogs,
    ROUND(SUM(f.net_profit), 2) AS net_profit,
    ROUND((SUM(f.net_profit) / SUM(f.net_revenue)) * 100, 2) AS net_margin_pct
FROM fact_order_items f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.order_status = 'Completed'
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- ============================================================================
-- QUERY 2: Product Performance Matrix (Volume vs. True Margin)
-- Business Objective: Identify which categories generate volume vs profit.
-- ============================================================================
SELECT 
    p.category,
    COUNT(f.sales_key) AS units_sold,
    ROUND(SUM(f.net_revenue), 2) AS total_net_revenue,
    ROUND(SUM(f.net_profit), 2) AS total_net_profit,
    ROUND((SUM(f.net_profit) / SUM(f.net_revenue)) * 100, 2) AS margin_contribution_pct
FROM fact_order_items f
JOIN dim_products p ON f.product_key = p.product_key
WHERE f.order_status = 'Completed'
GROUP BY p.category
ORDER BY total_net_profit DESC;


-- ============================================================================
-- QUERY 3: Customer Acquisition Channel Quality & Return Rates
-- Business Objective: Uncover which channels leak money via returns.
-- ============================================================================
SELECT 
    c.acquisition_channel,
    COUNT(DISTINCT f.order_id) AS total_orders_placed,
    COUNT(DISTINCT CASE WHEN f.order_status = 'Completed' THEN f.order_id END) AS completed_orders,
    COUNT(DISTINCT CASE WHEN f.order_status = 'Returned' THEN f.order_id END) AS returned_orders,
    ROUND(
        (COUNT(DISTINCT CASE WHEN f.order_status = 'Returned' THEN f.order_id END) * 1.0 / COUNT(DISTINCT f.order_id)) * 100, 
        2
    ) AS return_rate_pct,
    ROUND(SUM(CASE WHEN f.order_status = 'Completed' THEN f.net_revenue ELSE 0 END), 2) AS realized_net_revenue
FROM fact_order_items f
JOIN dim_customers c ON f.customer_key = c.customer_key
GROUP BY c.acquisition_channel
ORDER BY realized_net_revenue DESC;