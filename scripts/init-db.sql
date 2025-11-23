-- ===================================
-- SecureTempMail Database Initialization
-- ===================================
-- This script is run automatically by PostgreSQL on first startup
-- via docker-entrypoint-initdb.d/

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For better indexing

-- Set timezone
SET timezone = 'UTC';

-- Create custom types
DO $$ BEGIN
    CREATE TYPE inbox_status AS ENUM ('active', 'expired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE message_status AS ENUM ('received', 'read', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tempmail;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tempmail;

-- Create indexes for performance (will be created by SQLAlchemy too)
-- These are idempotent and safe to run

-- Logging
\echo 'Database initialized successfully';
\echo 'Extensions enabled: uuid-ossp, pg_trgm, btree_gin';
\echo 'Custom types created: inbox_status, message_status';
\echo 'Ready for application startup';