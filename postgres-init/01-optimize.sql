-- ============================================================================
-- PostgreSQL Performance Optimization for Bulk Loading
-- Run this AFTER init_db.sql but BEFORE data loading
-- ============================================================================

-- 1. Optimize for bulk insert (temporary settings for loading phase)
ALTER SYSTEM SET synchronous_commit = off;
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET max_wal_size = '4GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- 2. Disable auto-vacuum during bulk load (re-enable after)
ALTER TABLE silver.trips SET (autovacuum_enabled = false);

-- 3. Create indexes AFTER data load (comment out during initial load)
-- Uncomment these lines AFTER you've loaded all data:
--
-- CREATE INDEX IF NOT EXISTS idx_trips_pickup_date ON silver.trips(pickup_date);
-- CREATE INDEX IF NOT EXISTS idx_trips_pickup_month ON silver.trips(pickup_year, pickup_month);
-- CREATE INDEX IF NOT EXISTS idx_trips_pulocation ON silver.trips(pulocationid);
-- CREATE INDEX IF NOT EXISTS idx_trips_dolocation ON silver.trips(dolocationid);
--
-- ALTER TABLE silver.trips SET (autovacuum_enabled = true);

-- 4. Re-enable normal settings after load
-- ALTER SYSTEM RESET synchronous_commit;
-- ALTER SYSTEM RESET wal_buffers;
-- ALTER SYSTEM RESET max_wal_size;
