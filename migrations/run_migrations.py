#!/usr/bin/env python3
"""
Database migration runner for Causal AI Manufacturing Platform.

This script runs PostgreSQL migrations in the correct order and tracks
which migrations have been applied.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to path to import settings
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings


class MigrationRunner:
    """Handles database migration execution and tracking."""

    def __init__(self, connection_url: str):
        """Initialize migration runner with database connection."""
        self.connection_url = connection_url
        self.migrations_dir = Path(__file__).parent
        self.migration_files = [
            "001_create_causal_dags_table.sql",
            "002_create_station_models_table.sql",
            "003_create_audit_logs_table.sql",
            "004_create_supporting_tables.sql",
        ]

    def create_migration_tracking_table(self, conn: psycopg2.extensions.connection) -> None:
        """Create table to track applied migrations."""
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    error_message TEXT
                );
            """)
            conn.commit()
            print("✓ Migration tracking table ready")

    def get_applied_migrations(self, conn: psycopg2.extensions.connection) -> List[str]:
        """Get list of already applied migrations."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT migration_id 
                FROM schema_migrations 
                WHERE success = TRUE
                ORDER BY applied_at;
            """)
            return [row[0] for row in cur.fetchall()]

    def mark_migration_applied(
        self,
        conn: psycopg2.extensions.connection,
        migration_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark a migration as applied in the tracking table."""
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO schema_migrations (migration_id, success, error_message)
                VALUES (%s, %s, %s)
                ON CONFLICT (migration_id) DO UPDATE
                SET applied_at = CURRENT_TIMESTAMP,
                    success = EXCLUDED.success,
                    error_message = EXCLUDED.error_message;
            """,
                (migration_id, success, error_message),
            )
            conn.commit()

    def run_migration_file(
        self, conn: psycopg2.extensions.connection, migration_file: str
    ) -> bool:
        """Run a single migration file."""
        migration_path = self.migrations_dir / migration_file
        migration_id = migration_file.replace(".sql", "")

        print(f"\n{'='*70}")
        print(f"Running migration: {migration_file}")
        print(f"{'='*70}")

        try:
            # Read migration SQL
            with open(migration_path, "r") as f:
                migration_sql = f.read()

            # Execute migration
            with conn.cursor() as cur:
                cur.execute(migration_sql)
                conn.commit()

            # Mark as applied
            self.mark_migration_applied(conn, migration_id, success=True)
            print(f"✓ Migration {migration_file} completed successfully")
            return True

        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            print(f"✗ Migration {migration_file} failed: {error_msg}")
            self.mark_migration_applied(conn, migration_id, success=False, error_message=error_msg)
            return False

    def run_all_migrations(self) -> bool:
        """Run all pending migrations."""
        print(f"\nConnecting to database: {settings.postgres_db}")
        print(f"Host: {settings.postgres_host}:{settings.postgres_port}")
        print(f"User: {settings.postgres_user}\n")

        try:
            # Connect to database
            conn = psycopg2.connect(settings.postgres_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            # Create migration tracking table
            self.create_migration_tracking_table(conn)

            # Get already applied migrations
            applied_migrations = self.get_applied_migrations(conn)
            print(f"\nAlready applied migrations: {len(applied_migrations)}")
            for migration in applied_migrations:
                print(f"  ✓ {migration}")

            # Run pending migrations
            pending_migrations = [
                f
                for f in self.migration_files
                if f.replace(".sql", "") not in applied_migrations
            ]

            if not pending_migrations:
                print("\n✓ All migrations are up to date!")
                return True

            print(f"\nPending migrations: {len(pending_migrations)}")
            for migration in pending_migrations:
                print(f"  → {migration}")

            # Run each pending migration
            all_success = True
            for migration_file in pending_migrations:
                success = self.run_migration_file(conn, migration_file)
                if not success:
                    all_success = False
                    print(f"\n✗ Migration failed, stopping execution")
                    break

            conn.close()

            if all_success:
                print(f"\n{'='*70}")
                print("✓ All migrations completed successfully!")
                print(f"{'='*70}\n")
            else:
                print(f"\n{'='*70}")
                print("✗ Some migrations failed")
                print(f"{'='*70}\n")

            return all_success

        except psycopg2.Error as e:
            print(f"\n✗ Database connection error: {e}")
            return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            return False

    def run_specific_migration(self, migration_number: str) -> bool:
        """Run a specific migration by number."""
        # Find migration file matching the number
        matching_files = [f for f in self.migration_files if f.startswith(migration_number)]

        if not matching_files:
            print(f"✗ No migration found matching: {migration_number}")
            return False

        migration_file = matching_files[0]

        try:
            conn = psycopg2.connect(settings.postgres_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            self.create_migration_tracking_table(conn)
            success = self.run_migration_file(conn, migration_file)

            conn.close()
            return success

        except psycopg2.Error as e:
            print(f"\n✗ Database connection error: {e}")
            return False

    def show_status(self) -> None:
        """Show migration status."""
        try:
            conn = psycopg2.connect(settings.postgres_url)
            self.create_migration_tracking_table(conn)

            applied_migrations = self.get_applied_migrations(conn)

            print(f"\n{'='*70}")
            print("Migration Status")
            print(f"{'='*70}\n")

            for migration_file in self.migration_files:
                migration_id = migration_file.replace(".sql", "")
                status = "✓ Applied" if migration_id in applied_migrations else "○ Pending"
                print(f"{status:12} {migration_file}")

            print(f"\n{'='*70}")
            print(f"Total: {len(self.migration_files)} migrations")
            print(f"Applied: {len(applied_migrations)}")
            print(f"Pending: {len(self.migration_files) - len(applied_migrations)}")
            print(f"{'='*70}\n")

            conn.close()

        except psycopg2.Error as e:
            print(f"\n✗ Database connection error: {e}")


def main() -> int:
    """Main entry point for migration runner."""
    parser = argparse.ArgumentParser(
        description="Run database migrations for Causal AI Manufacturing Platform"
    )
    parser.add_argument(
        "--migration",
        "-m",
        type=str,
        help="Run specific migration by number (e.g., 001)",
    )
    parser.add_argument(
        "--status",
        "-s",
        action="store_true",
        help="Show migration status",
    )

    args = parser.parse_args()

    runner = MigrationRunner(settings.postgres_url)

    if args.status:
        runner.show_status()
        return 0

    if args.migration:
        success = runner.run_specific_migration(args.migration)
    else:
        success = runner.run_all_migrations()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
