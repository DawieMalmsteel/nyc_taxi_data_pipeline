-- ============================================================================
-- Run this AFTER loading data to add constraints and indexes
-- ============================================================================
-- Usage: psql -U nyc_user -d nyc_taxi -f scripts/post_load_optimize.sql
-- ============================================================================

-- 1. Add PRIMARY KEY constraint (much faster after data is loaded)
ALTER TABLE silver.trips ADD PRIMARY KEY (trip_id);

-- 2. Create indexes for analytics queries
CREATE INDEX IF NOT EXISTS idx_trips_pickup_date ON silver.trips(pickup_date);
CREATE INDEX IF NOT EXISTS idx_trips_pickup_month ON silver.trips(pickup_year, pickup_month);
CREATE INDEX IF NOT EXISTS idx_trips_pulocation ON silver.trips(pulocationid);
CREATE INDEX IF NOT EXISTS idx_trips_dolocation ON silver.trips(dolocationid);
CREATE INDEX IF NOT EXISTS idx_trips_payment_type ON silver.trips(payment_type);

-- 3. Analyze for query optimizer
ANALYZE silver.trips;

-- 4. Re-enable auto-vacuum
ALTER TABLE silver.trips SET (autovacuum_enabled = true);

SELECT 'Post-load optimization complete!' AS status;
