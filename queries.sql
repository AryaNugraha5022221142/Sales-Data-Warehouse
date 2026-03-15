-- ============================================================
-- SALES DATA WAREHOUSE — REPORTING QUERIES
-- Author: Arya Nugraha
-- Database: sales_dw | Schema: warehouse
-- Stack: PostgreSQL 18
-- ============================================================
-- ------------------------------------------------------------
-- SECTION 1: BASIC REPORTING
-- ------------------------------------------------------------

-- 1.1 Total Revenue by Product Category
SELECT
    p.category,
    SUM(f.totalsales)       AS total_revenue,
    SUM(f.totalprofit)      AS total_profit,
    COUNT(f.saleskey)       AS total_orders
FROM warehouse.factsales f
JOIN warehouse.dimproduct p ON f.productkey = p.productkey
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 1.2 Revenue by Region
-- (paste your existing region query here)


-- 1.3 Monthly Revenue Trend
-- (paste your existing monthly trend query here)


-- ------------------------------------------------------------
-- SECTION 2: WINDOW FUNCTIONS
-- ------------------------------------------------------------

-- 2.1 Month-over-Month Revenue Growth
SELECT
    d.year,
    d.monthofyear,
    d.monthname,
    SUM(f.totalsales)                                                        AS revenue,
    LAG(SUM(f.totalsales)) OVER (ORDER BY d.year, d.monthofyear)             AS prev_month_revenue,
    ROUND(
        (SUM(f.totalsales) - LAG(SUM(f.totalsales)) OVER (ORDER BY d.year, d.monthofyear))
        / NULLIF(LAG(SUM(f.totalsales)) OVER (ORDER BY d.year, d.monthofyear), 0) * 100, 2
    )                                                                        AS mom_growth_pct
FROM warehouse.factsales f
JOIN warehouse.dimdate d ON f.datekey = d.datekey
GROUP BY d.year, d.monthofyear, d.monthname
ORDER BY d.year, d.monthofyear;


-- 2.2 Running Cumulative Revenue by Day
SELECT
    d.fulldate,
    SUM(f.totalsales)                                                           AS daily_revenue,
    SUM(SUM(f.totalsales)) OVER (ORDER BY d.fulldate ROWS UNBOUNDED PRECEDING)  AS cumulative_revenue
FROM warehouse.factsales f
JOIN warehouse.dimdate d ON f.datekey = d.datekey
GROUP BY d.fulldate
ORDER BY d.fulldate;


-- ------------------------------------------------------------
-- SECTION 3: CTEs — CUSTOMER SEGMENTATION (RFM)
-- ------------------------------------------------------------

-- 3.1 RFM Scoring: Recency, Frequency, Monetary
WITH rfm AS (
    SELECT
        f.customerkey,
        MAX(d.fulldate)                         AS last_purchase,
        COUNT(*)                                AS frequency,
        SUM(f.totalsales)                       AS monetary,
        CURRENT_DATE - MAX(d.fulldate)          AS recency_days
    FROM warehouse.factsales f
    JOIN warehouse.dimdate d ON f.datekey = d.datekey
    GROUP BY f.customerkey
),
rfm_scored AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY recency_days ASC)   AS r_score,
        NTILE(4) OVER (ORDER BY frequency DESC)     AS f_score,
        NTILE(4) OVER (ORDER BY monetary DESC)      AS m_score
    FROM rfm
)
SELECT *,
    CONCAT(r_score, f_score, m_score)               AS rfm_segment
FROM rfm_scored
ORDER BY monetary DESC;
