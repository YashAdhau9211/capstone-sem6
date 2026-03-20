# Database Migrations

This directory contains PostgreSQL database schema migrations for the Causal AI Manufacturing Platform.

## Migration Files

The migrations are numbered sequentially and should be applied in order:

1. **001_create_causal_dags_table.sql** - Creates the `causal_dags` table with versioning support
   - Stores versioned causal DAGs for each manufacturing station
   - Implements automatic version history limit (50 versions per station)
   - Requirements: 7.8, 14.5, 22.9

2. **002_create_station_models_table.sql** - Creates the `station_models` table
   - Stores causal models for each manufacturing station
   - Links to current active DAG version
   - Tracks model status and baseline accuracy
   - Requirements: 14.1, 14.2, 14.5, 14.6, 21.2

3. **003_create_audit_logs_table.sql** - Creates the `audit_logs` table
   - Immutable audit logging of all user actions and system decisions
   - Write-only permissions (no updates/deletes)
   - 2-year retention policy with archival support
   - Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7

4. **004_create_supporting_tables.sql** - Creates supporting tables
   - `user_preferences` - User notification channels and UI settings
   - `notifications` - Notification events and delivery status
   - `performance_metrics` - System and station performance monitoring
   - Requirements: 27.7, 28.1

## Running Migrations

### Using the Python Migration Script

```bash
# Run all migrations
python migrations/run_migrations.py

# Run specific migration
python migrations/run_migrations.py --migration 001

# Rollback last migration (if rollback script exists)
python migrations/run_migrations.py --rollback
```

### Using psql Command Line

```bash
# Connect to database
psql -h localhost -U causal_user -d causal_ai_db

# Run migrations in order
\i migrations/001_create_causal_dags_table.sql
\i migrations/002_create_station_models_table.sql
\i migrations/003_create_audit_logs_table.sql
\i migrations/004_create_supporting_tables.sql
```

### Using Docker Compose

If using the provided `docker-compose.yml`:

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Run migrations
docker-compose exec postgres psql -U causal_user -d causal_ai_db -f /migrations/001_create_causal_dags_table.sql
docker-compose exec postgres psql -U causal_user -d causal_ai_db -f /migrations/002_create_station_models_table.sql
docker-compose exec postgres psql -U causal_user -d causal_ai_db -f /migrations/003_create_audit_logs_table.sql
docker-compose exec postgres psql -U causal_user -d causal_ai_db -f /migrations/004_create_supporting_tables.sql
```

## Database Schema Overview

### Core Tables

- **causal_dags** - Versioned causal DAG storage
  - Primary key: `dag_id` (UUID)
  - Unique constraint: `(station_id, version)`
  - Indexes: `station_id`, `created_at`
  - Automatic version limiting (50 versions per station)

- **station_models** - Station-specific causal models
  - Primary key: `model_id` (UUID)
  - Unique constraint: `station_id`
  - Foreign key: `current_dag_id` → `causal_dags(dag_id)`
  - Indexes: `status`, `station_id`

- **audit_logs** - Immutable audit trail
  - Primary key: `log_id` (UUID)
  - Indexes: `timestamp`, `user_id`, `action_type`, `resource_type`, `result`
  - Write-only (updates/deletes prevented by triggers)

### Supporting Tables

- **user_preferences** - User settings and preferences
  - Primary key: `user_id` (VARCHAR)
  - Stores notification channels, default station, UI preferences

- **notifications** - Notification events and delivery tracking
  - Primary key: `notification_id` (UUID)
  - Indexes: `event_type`, `created_at`, `priority`, `delivered_at`

- **performance_metrics** - System performance monitoring
  - Primary key: `metric_id` (UUID)
  - Indexes: `metric_type`, `station_id`, `timestamp`, `aggregation_period`

## Key Features

### Automatic Version Management
- DAG versions are automatically incremented per station
- Version history is limited to 50 versions per station
- Oldest versions are automatically deleted when limit is reached

### Data Integrity
- Foreign key constraints ensure referential integrity
- Check constraints validate data ranges and enums
- Unique constraints prevent duplicate entries

### Audit Trail Protection
- Audit logs cannot be updated or deleted (enforced by triggers)
- All modifications are logged with user, timestamp, and details
- 2-year retention policy with archival support

### Performance Optimization
- Strategic indexes on frequently queried columns
- Composite indexes for common query patterns
- Partial indexes for filtered queries (e.g., undelivered notifications)

### Automatic Timestamp Management
- `created_at` defaults to current timestamp
- `updated_at` automatically updated on row modifications
- Triggers ensure consistency

## Maintenance Functions

### Version History Cleanup
```sql
-- Manually trigger version cleanup for a station
SELECT enforce_dag_version_limit() FROM causal_dags WHERE station_id = 'furnace-01';
```

### Audit Log Archival
```sql
-- Archive audit logs older than 2 years
SELECT * FROM archive_old_audit_logs();
```

### Performance Metrics Cleanup
```sql
-- Clean up old performance metrics
SELECT * FROM cleanup_old_performance_metrics();
```

## Views

### audit_logs_active
Shows audit logs within the 2-year retention policy.

### recent_notifications
Shows notifications from the last 30 days.

### undelivered_notifications
Shows notifications that haven't been delivered yet, ordered by priority.

### system_performance_24h
Aggregated system-wide performance metrics for the last 24 hours.

## Configuration

Database connection settings are configured in `config/settings.py`:

```python
postgres_host: str = "localhost"
postgres_port: int = 5432
postgres_db: str = "causal_ai_db"
postgres_user: str = "causal_user"
postgres_password: str = "causal_pass"
```

Override these settings using environment variables or a `.env` file.

## Troubleshooting

### Migration Already Applied
If you see "relation already exists" errors, the migration has already been applied. All migrations use `IF NOT EXISTS` clauses to be idempotent.

### Permission Errors
Ensure the database user has sufficient privileges:
```sql
GRANT ALL PRIVILEGES ON DATABASE causal_ai_db TO causal_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO causal_user;
```

### Connection Errors
Verify database connection settings in `config/settings.py` or `.env` file.

## Future Enhancements

Consider using a migration management tool for production:
- **Alembic** - Python-based migration tool with version tracking
- **Flyway** - Java-based migration tool with checksum verification
- **Liquibase** - Database-agnostic migration tool with rollback support

These tools provide:
- Automatic migration tracking
- Rollback capabilities
- Migration validation
- Team collaboration features
