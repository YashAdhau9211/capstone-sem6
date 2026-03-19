-- Migration: 002_create_station_models_table.sql
-- Description: Create station_models table for per-station causal models
-- Requirements: 14.1, 14.2, 14.5, 14.6, 21.2
-- Task: 7.2 Create station_models table

-- Create station_models table
CREATE TABLE IF NOT EXISTS station_models (
    model_id UUID PRIMARY KEY,
    station_id VARCHAR(100) UNIQUE NOT NULL,
    current_dag_id UUID REFERENCES causal_dags(dag_id) ON DELETE SET NULL,
    baseline_accuracy FLOAT,
    last_evaluated TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'training',
    config JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('active', 'drifted', 'training', 'archived'))
);

-- Add index on status field for filtering
CREATE INDEX IF NOT EXISTS idx_station_models_status ON station_models(status);

-- Add index on station_id for lookups (already unique, but explicit index helps)
CREATE INDEX IF NOT EXISTS idx_station_models_station_id ON station_models(station_id);

-- Add comments for documentation
COMMENT ON TABLE station_models IS 'Stores causal models for each manufacturing station';
COMMENT ON COLUMN station_models.model_id IS 'Unique identifier for the station model';
COMMENT ON COLUMN station_models.station_id IS 'Manufacturing station identifier (unique per station)';
COMMENT ON COLUMN station_models.current_dag_id IS 'Foreign key to current active DAG version';
COMMENT ON COLUMN station_models.baseline_accuracy IS 'Baseline prediction accuracy established during validation';
COMMENT ON COLUMN station_models.last_evaluated IS 'Timestamp of last model evaluation';
COMMENT ON COLUMN station_models.status IS 'Model status: active, drifted, training, or archived';
COMMENT ON COLUMN station_models.config IS 'Model configuration including retraining schedule and drift thresholds';
COMMENT ON COLUMN station_models.created_at IS 'Timestamp when model was created';
COMMENT ON COLUMN station_models.updated_at IS 'Timestamp when model was last updated';

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_station_models_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_station_models_updated_at ON station_models;
CREATE TRIGGER trigger_update_station_models_updated_at
    BEFORE UPDATE ON station_models
    FOR EACH ROW
    EXECUTE FUNCTION update_station_models_updated_at();

-- Function to validate baseline_accuracy range
CREATE OR REPLACE FUNCTION validate_baseline_accuracy()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.baseline_accuracy IS NOT NULL AND (NEW.baseline_accuracy < 0 OR NEW.baseline_accuracy > 1) THEN
        RAISE EXCEPTION 'baseline_accuracy must be between 0 and 1, got %', NEW.baseline_accuracy;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to validate baseline_accuracy
DROP TRIGGER IF EXISTS trigger_validate_baseline_accuracy ON station_models;
CREATE TRIGGER trigger_validate_baseline_accuracy
    BEFORE INSERT OR UPDATE ON station_models
    FOR EACH ROW
    EXECUTE FUNCTION validate_baseline_accuracy();
