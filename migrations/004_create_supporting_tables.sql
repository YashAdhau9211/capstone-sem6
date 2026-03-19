-- Migration: 004_create_supporting_tables.sql
-- Description: Create supporting tables (user_preferences, notifications, performance_metrics)
-- Requirements: 27.7, 28.1
-- Task: 7.4 Create supporting tables

-- ============================================================================
-- User Preferences Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(100) PRIMARY KEY,
    notification_channels JSONB DEFAULT '{"email": true, "sms": false, "webhook": false}'::jsonb,
    default_station_id VARCHAR(100),
    ui_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add index for station lookups
CREATE INDEX IF NOT EXISTS idx_user_preferences_station ON user_preferences(default_station_id);

-- Add comments for documentation
COMMENT ON TABLE user_preferences IS 'Stores user-specific preferences and settings';
COMMENT ON COLUMN user_preferences.user_id IS 'Unique user identifier';
COMMENT ON COLUMN user_preferences.notification_channels IS 'Notification channel preferences (email, SMS, webhook)';
COMMENT ON COLUMN user_preferences.default_station_id IS 'Default manufacturing station for the user';
COMMENT ON COLUMN user_preferences.ui_preferences IS 'UI-specific preferences (theme, layout, etc.)';
COMMENT ON COLUMN user_preferences.created_at IS 'Timestamp when preferences were created';
COMMENT ON COLUMN user_preferences.updated_at IS 'Timestamp when preferences were last updated';

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_user_preferences_updated_at ON user_preferences;
CREATE TRIGGER trigger_update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_user_preferences_updated_at();

-- ============================================================================
-- Notifications Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    recipients JSONB NOT NULL,
    channels JSONB NOT NULL,
    content JSONB NOT NULL,
    delivery_status JSONB DEFAULT '{}'::jsonb,
    priority VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

-- Add indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_notifications_event_type ON notifications(event_type);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notifications(priority);
CREATE INDEX IF NOT EXISTS idx_notifications_delivered_at ON notifications(delivered_at);

-- Composite index for undelivered notifications
CREATE INDEX IF NOT EXISTS idx_notifications_undelivered ON notifications(created_at) 
WHERE delivered_at IS NULL;

-- Add comments for documentation
COMMENT ON TABLE notifications IS 'Stores notification events and delivery status';
COMMENT ON COLUMN notifications.notification_id IS 'Unique identifier for the notification';
COMMENT ON COLUMN notifications.event_type IS 'Type of event that triggered the notification';
COMMENT ON COLUMN notifications.recipients IS 'List of recipient user IDs in JSON format';
COMMENT ON COLUMN notifications.channels IS 'Delivery channels to use (email, SMS, webhook)';
COMMENT ON COLUMN notifications.content IS 'Notification content including subject, body, and metadata';
COMMENT ON COLUMN notifications.delivery_status IS 'Delivery status per channel and recipient';
COMMENT ON COLUMN notifications.priority IS 'Notification priority: low, medium, high, or critical';
COMMENT ON COLUMN notifications.created_at IS 'Timestamp when notification was created';
COMMENT ON COLUMN notifications.delivered_at IS 'Timestamp when notification was successfully delivered';

-- ============================================================================
-- Performance Metrics Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id UUID PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,
    station_id VARCHAR(100),
    value FLOAT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    aggregation_period VARCHAR(20),
    CONSTRAINT valid_aggregation_period CHECK (
        aggregation_period IS NULL OR 
        aggregation_period IN ('raw', 'hourly', 'daily', 'weekly', 'monthly')
    )
);

-- Add indexes for performance monitoring queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_station ON performance_metrics(station_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_aggregation ON performance_metrics(aggregation_period);

-- Composite index for time-series queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type_timestamp 
ON performance_metrics(metric_type, timestamp);

-- Composite index for station-specific queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics_station_type_timestamp 
ON performance_metrics(station_id, metric_type, timestamp);

-- Add comments for documentation
COMMENT ON TABLE performance_metrics IS 'Stores system and station performance metrics for monitoring';
COMMENT ON COLUMN performance_metrics.metric_id IS 'Unique identifier for the metric entry';
COMMENT ON COLUMN performance_metrics.metric_type IS 'Type of metric (query_latency, uptime, energy_savings, yield_improvement, etc.)';
COMMENT ON COLUMN performance_metrics.station_id IS 'Manufacturing station identifier (NULL for system-wide metrics)';
COMMENT ON COLUMN performance_metrics.value IS 'Metric value';
COMMENT ON COLUMN performance_metrics.timestamp IS 'Timestamp when metric was recorded';
COMMENT ON COLUMN performance_metrics.metadata IS 'Additional metric metadata in JSON format';
COMMENT ON COLUMN performance_metrics.aggregation_period IS 'Aggregation period for the metric (raw, hourly, daily, etc.)';

-- Function to clean up old raw performance metrics (keep aggregated data longer)
CREATE OR REPLACE FUNCTION cleanup_old_performance_metrics()
RETURNS TABLE(deleted_count BIGINT) AS $$
DECLARE
    raw_cutoff_date TIMESTAMP;
    aggregated_cutoff_date TIMESTAMP;
    deleted_count BIGINT := 0;
BEGIN
    -- Raw metrics: keep for 90 days
    raw_cutoff_date := CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    -- Aggregated metrics: keep for 2 years
    aggregated_cutoff_date := CURRENT_TIMESTAMP - INTERVAL '2 years';
    
    -- Delete old raw metrics
    WITH deleted_raw AS (
        DELETE FROM performance_metrics
        WHERE timestamp < raw_cutoff_date
        AND (aggregation_period = 'raw' OR aggregation_period IS NULL)
        RETURNING *
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted_raw;
    
    -- Delete old aggregated metrics
    WITH deleted_aggregated AS (
        DELETE FROM performance_metrics
        WHERE timestamp < aggregated_cutoff_date
        AND aggregation_period IN ('hourly', 'daily', 'weekly', 'monthly')
        RETURNING *
    )
    SELECT deleted_count + COUNT(*) INTO deleted_count FROM deleted_aggregated;
    
    RETURN QUERY SELECT deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_performance_metrics IS 'Cleans up old performance metrics based on retention policy';

-- ============================================================================
-- Helper Views
-- ============================================================================

-- View for recent notifications (last 30 days)
CREATE OR REPLACE VIEW recent_notifications AS
SELECT *
FROM notifications
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY created_at DESC;

COMMENT ON VIEW recent_notifications IS 'View of notifications from the last 30 days';

-- View for undelivered notifications
CREATE OR REPLACE VIEW undelivered_notifications AS
SELECT *
FROM notifications
WHERE delivered_at IS NULL
ORDER BY priority DESC, created_at ASC;

COMMENT ON VIEW undelivered_notifications IS 'View of notifications that have not been delivered yet';

-- View for system-wide performance metrics (last 24 hours)
CREATE OR REPLACE VIEW system_performance_24h AS
SELECT 
    metric_type,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(*) as sample_count
FROM performance_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
AND station_id IS NULL
GROUP BY metric_type;

COMMENT ON VIEW system_performance_24h IS 'Aggregated system-wide performance metrics for the last 24 hours';
