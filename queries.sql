-- ============================================
-- SALES DATA WAREHOUSE - REPORTING QUERIES
-- ============================================


-- ============================================
-- QUERY 1: Total Revenue by Product Category
-- ============================================
SELECT 
    p.category,
    SUM(f.totalsales) AS total_revenue,
    COUNT(f.orderid)  AS total_orders
FROM warehouse.factsales f
JOIN warehouse.dimproduct p ON f.productkey = p.productkey
GROUP BY p.category
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 2: Monthly Sales Trend
-- ============================================
SELECT 
    d.year,
    d.monthname,
    d.monthofyear,
    SUM(f.totalsales)  AS monthly_revenue,
    COUNT(f.orderid)   AS total_orders
FROM warehouse.factsales f
JOIN warehouse.dimdate d ON f.datekey = d.datekey
GROUP BY d.year, d.monthname, d.monthofyear
ORDER BY d.year, d.monthofyear;


-- ============================================
-- QUERY 3: Top 10 Customers by Spend
-- ============================================
SELECT 
    c.customername,
    c.segment,
    c.region,
    SUM(f.totalsales)  AS total_spent,
    COUNT(f.orderid)   AS total_orders
FROM warehouse.factsales f
JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey
GROUP BY c.customername, c.segment, c.region
ORDER BY total_spent DESC
LIMIT 10;


-- ============================================
-- QUERY 4: Sales Performance by Region
-- ============================================
SELECT 
    c.region,
    SUM(f.totalsales)  AS total_revenue,
    COUNT(f.orderid)   AS total_orders,
    ROUND(AVG(f.totalsales)::numeric, 2) AS avg_order_value
FROM warehouse.factsales f
JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey
GROUP BY c.region
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 5: Top 10 Best Selling Products
-- ============================================
SELECT 
    p.productname,
    p.category,
    p.subcategory,
    SUM(f.totalsales)  AS total_revenue,
    COUNT(f.orderid)   AS total_orders
FROM warehouse.factsales f
JOIN warehouse.dimproduct p ON f.productkey = p.productkey
GROUP BY p.productname, p.category, p.subcategory
ORDER BY total_revenue DESC
LIMIT 10;


-- ============================================
-- QUERY 6: Yearly Revenue Growth
-- ============================================
SELECT 
    d.year,
    SUM(f.totalsales) AS yearly_revenue,
    LAG(SUM(f.totalsales)) OVER (ORDER BY d.year) AS prev_year_revenue,
    ROUND(
        (SUM(f.totalsales) - LAG(SUM(f.totalsales)) OVER (ORDER BY d.year)) 
        / LAG(SUM(f.totalsales)) OVER (ORDER BY d.year) * 100, 2
    ) AS growth_pct
FROM warehouse.factsales f
JOIN warehouse.dimdate d ON f.datekey = d.datekey
GROUP BY d.year
ORDER BY d.year;


-- ============================================
-- QUERY 7: Customer Segment Analysis
-- ============================================
SELECT 
    c.segment,
    COUNT(DISTINCT c.customerkey) AS total_customers,
    SUM(f.totalsales)             AS total_revenue,
    ROUND(AVG(f.totalsales)::numeric, 2) AS avg_order_value
FROM warehouse.factsales f
JOIN warehouse.dimcustomer c ON f.customerkey = c.customerkey
GROUP BY c.segment
ORDER BY total_revenue DESC;


-- ============================================
-- QUERY 8: Top Subcategories per Category
-- ============================================
SELECT 
    p.category,
    p.subcategory,
    SUM(f.totalsales) AS total_revenue,
    RANK() OVER (PARTITION BY p.category ORDER BY SUM(f.totalsales) DESC) AS rank_in_category
FROM warehouse.factsales f
JOIN warehouse.dimproduct p ON f.productkey = p.productkey
GROUP BY p.category, p.subcategory
ORDER BY p.category, rank_in_category;
