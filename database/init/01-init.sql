-- ARC PDF Tool Database Initialization
-- This script sets up the initial database structure and permissions

-- Ensure the database exists
SELECT 'CREATE DATABASE arc_pdf_tool'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'arc_pdf_tool');

-- Connect to the arc_pdf_tool database
\c arc_pdf_tool;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create schemas if they don't exist
CREATE SCHEMA IF NOT EXISTS arc;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions to arc_user
GRANT ALL PRIVILEGES ON DATABASE arc_pdf_tool TO arc_user;
GRANT ALL PRIVILEGES ON SCHEMA arc TO arc_user;
GRANT ALL PRIVILEGES ON SCHEMA audit TO arc_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA arc TO arc_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA arc TO arc_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA arc TO arc_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA arc GRANT ALL ON TABLES TO arc_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA arc GRANT ALL ON SEQUENCES TO arc_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA arc GRANT ALL ON FUNCTIONS TO arc_user;

-- Create audit table for tracking changes
CREATE TABLE IF NOT EXISTS audit.activity_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_name VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON audit.activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_log_table ON audit.activity_log(table_name);

-- Insert initial configuration
INSERT INTO arc.config (key, value, description) VALUES
    ('app_version', '1.0.0', 'Application version'),
    ('database_version', '1.0.0', 'Database schema version'),
    ('initialized_at', NOW()::text, 'Database initialization timestamp')
ON CONFLICT (key) DO NOTHING;