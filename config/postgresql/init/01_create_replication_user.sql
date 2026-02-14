-- Create replication user for PostgreSQL streaming replication
-- This script runs automatically on primary database initialization

-- Create replication role
CREATE ROLE replication WITH REPLICATION LOGIN PASSWORD 'replication_password';

-- Grant necessary privileges
GRANT CONNECT ON DATABASE trustwise_dev TO replication;

-- Log
SELECT 'Replication user created successfully' AS status;
