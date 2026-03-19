-- Migration: 001_create_causal_dags_table.sql
-- Description: Create causal_dags table with versioning support
-- Requirements: 7.8, 14.5, 22.9
-- Task: 7.1 Create causal_dags table with versioning

-- Create causal_dags table
CREATE TABLE IF NOT EXISTS causal_dags (
    dag_id UUID PRIMARY KEY,
    station_id VARCHAR(100) NOT NULL,
    version INT NOT NULL,
    dag_data JSONB NOT NULL,
    algorithm VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    parent_version INT,
    CONSTRAINT unique_station_version UNIQUE(station_id, version)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_causal_dags_station_id ON causal_dags(station_id);
CREATE INDEX IF NOT EXISTS idx_causal_dags_created_at ON causal_dags(created_at);

-- Add comments for documentation
COMMENT ON TABLE causal_dags IS 'Stores versioned causal DAGs for each manufacturing station';
COMMENT ON COLUMN causal_dags.dag_id IS 'Unique identifier for the DAG version';
COMMENT ON COLUMN causal_dags.station_id IS 'Manufacturing station identifier';
COMMENT ON COLUMN causal_dags.version IS 'Version number for this station DAG';
COMMENT ON COLUMN causal_dags.dag_data IS 'Serialized causal DAG structure in JSON format';
COMMENT ON COLUMN causal_dags.algorithm IS 'Algorithm used to generate DAG (DirectLiNGAM, RESIT, expert_edited)';
COMMENT ON COLUMN causal_dags.created_at IS 'Timestamp when this DAG version was created';
COMMENT ON COLUMN causal_dags.created_by IS 'User identifier who created this DAG version';
COMMENT ON COLUMN causal_dags.parent_version IS 'Parent version number for tracking modifications';

-- Function to enforce version history limit (50 versions per station)
CREATE OR REPLACE FUNCTION enforce_dag_version_limit()
RETURNS TRIGGER AS $$
DECLARE
    version_count INT;
BEGIN
    -- Count existing versions for this station
    SELECT COUNT(*) INTO version_count
    FROM causal_dags
    WHERE station_id = NEW.station_id;
    
    -- If we have 50 or more versions, delete the oldest one
    IF version_count >= 50 THEN
        DELETE FROM causal_dags
        WHERE dag_id = (
            SELECT dag_id
            FROM causal_dags
            WHERE station_id = NEW.station_id
            ORDER BY created_at ASC
            LIMIT 1
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce version limit
DROP TRIGGER IF EXISTS trigger_enforce_dag_version_limit ON causal_dags;
CREATE TRIGGER trigger_enforce_dag_version_limit
    BEFORE INSERT ON causal_dags
    FOR EACH ROW
    EXECUTE FUNCTION enforce_dag_version_limit();

-- Function to auto-increment version number
CREATE OR REPLACE FUNCTION auto_increment_dag_version()
RETURNS TRIGGER AS $$
BEGIN
    -- If version is not provided, auto-increment
    IF NEW.version IS NULL THEN
        SELECT COALESCE(MAX(version), 0) + 1 INTO NEW.version
        FROM causal_dags
        WHERE station_id = NEW.station_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for auto-increment version
DROP TRIGGER IF EXISTS trigger_auto_increment_dag_version ON causal_dags;
CREATE TRIGGER trigger_auto_increment_dag_version
    BEFORE INSERT ON causal_dags
    FOR EACH ROW
    EXECUTE FUNCTION auto_increment_dag_version();
