-- ============================================================================
-- NYC Taxi Analytics Queries
-- ============================================================================
-- These queries answer the required business questions.
-- Run after dbt models are built and data is in PostgreSQL.
-- ============================================================================

-- 1. What is total revenue by day?
SELECT
    pickup_date,
    total_trips,
    ROUND(total_revenue, 2) AS total_revenue,
    ROUND(avg_revenue_per_trip, 2) AS avg_revenue_per_trip
FROM mart_revenue_by_day
ORDER BY pickup_date;


-- 2. What is total trip count by day?
SELECT
    pickup_date,
    total_trips
FROM mart_revenue_by_day
ORDER BY pickup_date;


-- 3. Which pickup zones generate the most revenue?
SELECT
    location_id,
    borough,
    zone_name,
    total_trips,
    ROUND(total_revenue, 2) AS total_revenue,
    ROUND(avg_revenue, 2) AS avg_revenue
FROM mart_revenue_by_zone
WHERE direction = 'pickup'
ORDER BY total_revenue DESC
LIMIT 10;


-- 4. Which drop-off zones are most popular?
SELECT
    location_id,
    borough,
    zone_name,
    total_trips,
    ROUND(total_revenue, 2) AS total_revenue
FROM mart_revenue_by_zone
WHERE direction = 'dropoff'
ORDER BY total_trips DESC
LIMIT 10;


-- 5. What is the average fare by pickup borough?
SELECT
    pickup_borough,
    COUNT(*) AS total_trips,
    ROUND(AVG(fare_amount), 2) AS avg_fare,
    ROUND(AVG(total_amount), 2) AS avg_total,
    ROUND(SUM(total_amount), 2) AS total_revenue
FROM fact_trips
GROUP BY pickup_borough
ORDER BY avg_fare DESC;


-- 6. What is the average trip distance by hour?
SELECT
    pickup_hour,
    total_trips,
    ROUND(avg_distance, 2) AS avg_distance_miles,
    ROUND(avg_fare, 2) AS avg_fare,
    ROUND(avg_duration_minutes, 2) AS avg_duration_minutes
FROM mart_trips_by_hour
ORDER BY pickup_hour;


-- 7. Which payment type has the highest average tip?
SELECT
    payment_type_name,
    total_trips,
    ROUND(avg_tip, 2) AS avg_tip,
    ROUND(avg_tip_percentage, 2) AS avg_tip_percentage,
    percentage_of_trips
FROM mart_payment_type_summary
ORDER BY avg_tip DESC;


-- 8. What are the busiest pickup hours?
SELECT
    pickup_hour,
    total_trips,
    ROUND(total_revenue, 2) AS total_revenue
FROM mart_trips_by_hour
ORDER BY total_trips DESC;


-- 9. What percentage of records were invalid?
-- (This uses the quality report JSON; for SQL version, compare raw vs silver counts)
SELECT
    'Total Raw Records' AS metric,
    (SELECT COUNT(*) FROM raw.trips) AS value  -- Adjust table name as needed
UNION ALL
SELECT
    'Valid Silver Records' AS metric,
    (SELECT COUNT(*) FROM silver.trips) AS value
UNION ALL
SELECT
    'Invalid Records' AS metric,
    (SELECT COUNT(*) FROM raw.trips) - (SELECT COUNT(*) FROM silver.trips) AS value
UNION ALL
SELECT
    'Invalid Percentage' AS metric,
    ROUND(
        ((SELECT COUNT(*) FROM raw.trips) - (SELECT COUNT(*) FROM silver.trips)) * 100.0
        / NULLIF((SELECT COUNT(*) FROM raw.trips), 0),
        2
    ) AS value;


-- 10. Which routes have the highest average fare?
SELECT
    pickup_zone,
    dropoff_zone,
    pickup_borough,
    dropoff_borough,
    COUNT(*) AS trip_count,
    ROUND(AVG(fare_amount), 2) AS avg_fare,
    ROUND(AVG(total_amount), 2) AS avg_total,
    ROUND(AVG(trip_distance), 2) AS avg_distance
FROM fact_trips
GROUP BY pickup_zone, dropoff_zone, pickup_borough, dropoff_borough
HAVING COUNT(*) >= 100  -- Only routes with significant volume
ORDER BY avg_fare DESC
LIMIT 10;


-- ============================================================================
-- BONUS: Additional useful analytics
-- ============================================================================

-- Revenue by borough combination (pickup → dropoff)
SELECT
    pickup_borough,
    dropoff_borough,
    COUNT(*) AS trips,
    ROUND(SUM(total_amount), 2) AS total_revenue,
    ROUND(AVG(total_amount), 2) AS avg_revenue
FROM fact_trips
GROUP BY pickup_borough, dropoff_borough
ORDER BY total_revenue DESC;

-- Tip analysis by hour
SELECT
    pickup_hour,
    COUNT(*) AS trips,
    ROUND(AVG(tip_amount), 2) AS avg_tip,
    ROUND(AVG(tip_percentage), 2) AS avg_tip_pct,
    SUM(CASE WHEN has_tip THEN 1 ELSE 0 END) AS trips_with_tip,
    ROUND(
        SUM(CASE WHEN has_tip THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS pct_with_tip
FROM fact_trips
GROUP BY pickup_hour
ORDER BY pickup_hour;
