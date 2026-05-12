#!/usr/bin/env python3
"""
Database Migration Runner for Zenvort
=====================================
Runs pending SQL migrations in order.

Usage:
    python run_migrations.py                    # Run all pending migrations
    python run_migrations.py --status            # Show migration status
    python run_migrations.py --rollback <name>    # Rollback a migration (if supported)

Environment:
    DB_PATH     Path to SQLite database (default: from .env or ./zenvort.db)
"""

import os
import sys
import re
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add app to path for config
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings


def get_migration_dir() -> Path:
    """Get the migrations directory."""
    return Path(__file__).parent / "migrations"


def get_db_path() -> str:
    """Get database path from settings or env."""
    try:
        return get_settings().DB_PATH
    except Exception:
        return os.getenv("DB_PATH", "./zenvort.db")


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """Create migrations tracking table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL,
            checksum TEXT
        )
    """)
    conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """Get set of already-applied migration names."""
    cursor = conn.execute("SELECT name FROM _migrations")
    return {row[0] for row in cursor.fetchall()}


def get_pending_migrations(conn: sqlite3.Connection) -> list[Path]:
    """Get list of pending migration files."""
    applied = get_applied_migrations(conn)
    migration_dir = get_migration_dir()
    
    all_migrations = []
    for f in sorted(migration_dir.glob("*.sql")):
        if f.stem not in applied:
            all_migrations.append(f)
    
    return all_migrations


def parse_migration_name(filename: str) -> tuple[int, str]:
    """Parse migration filename into (sequence, name)."""
    match = re.match(r"^(\d+)_(.+)\.sql$", filename)
    if not match:
        raise ValueError(f"Invalid migration filename: {filename}. Expected format: NNN_name.sql")
    return int(match.group(1)), match.group(2)


def apply_migration(conn: sqlite3.Connection, migration_path: Path) -> bool:
    """Apply a single migration file."""
    name = migration_path.stem
    sequence, _ = parse_migration_name(migration_path.name)
    
    # Read SQL content
    sql = migration_path.read_text()
    
    # Split into statements (simple split, handles most cases)
    # For complex migrations, you may need a proper SQL parser
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    
    try:
        # Begin transaction
        cursor = conn.cursor()
        
        # Execute each statement
        for stmt in statements:
            if stmt:
                cursor.execute(stmt)
        
        # Record migration
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO _migrations (name, applied_at) VALUES (?, ?)",
            (name, now)
        )
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Migration {name} failed: {e}")


def rollback_migration(conn: sqlite3.Connection, name: str) -> bool:
    """Rollback a migration (if it has a rollback section)."""
    migration_dir = get_migration_dir()
    migration_path = migration_dir / f"{name}.sql"
    
    if not migration_path.exists():
        raise FileNotFoundError(f"Migration {name} not found")
    
    # Check if migration has rollback section
    sql = migration_path.read_text()
    
    if "-- ROLLBACK" not in sql:
        print(f"Migration {name} has no rollback section. Skipping.")
        return False
    
    # Extract rollback statements
    rollback_section = sql.split("-- ROLLBACK")[1]
    statements = [s.strip() for s in rollback_section.split(";") if s.strip()]
    
    try:
        cursor = conn.cursor()
        for stmt in statements:
            if stmt:
                cursor.execute(stmt)
        
        conn.execute("DELETE FROM _migrations WHERE name = ?", (name,))
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Rollback of {name} failed: {e}")


def show_status(db_path: str) -> None:
    """Show migration status."""
    conn = sqlite3.connect(db_path)
    ensure_migrations_table(conn)
    
    applied = get_applied_migrations(conn)
    migration_dir = get_migration_dir()
    
    print("\n" + "=" * 60)
    print("MIGRATION STATUS")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Migrations dir: {migration_dir}")
    print()
    
    # Show all migrations
    for f in sorted(migration_dir.glob("*.sql")):
        name = f.stem
        if name in applied:
            status = "✅ APPLIED"
        else:
            status = "⏳ PENDING"
        print(f"  {name:40} {status}")
    
    print()
    print(f"Applied: {len(applied)}")
    print(f"Pending: {len(list(migration_dir.glob('*.sql'))) - len(applied)}")
    print("=" * 60 + "\n")
    
    conn.close()


def run_migrations(db_path: str, dry_run: bool = False) -> int:
    """Run all pending migrations. Returns number applied."""
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    ensure_migrations_table(conn)
    
    pending = get_pending_migrations(conn)
    
    if not pending:
        print("✅ All migrations applied. Nothing to do.")
        conn.close()
        return 0
    
    print(f"\n📦 Found {len(pending)} pending migration(s)")
    print()
    
    applied_count = 0
    
    for migration_path in pending:
        name = migration_path.stem
        print(f"  Applying: {name}...")
        
        if dry_run:
            print(f"    [DRY RUN] Would apply {migration_path}")
            applied_count += 1
            continue
        
        try:
            apply_migration(conn, migration_path)
            print(f"    ✅ Applied: {name}")
            applied_count += 1
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            conn.close()
            return -1
    
    conn.close()
    
    if applied_count > 0:
        print(f"\n✅ Applied {applied_count} migration(s)")
    else:
        print("\n✅ No migrations to apply")
    
    return applied_count


def main():
    parser = argparse.ArgumentParser(description="Zenvort Database Migration Runner")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied")
    parser.add_argument("--rollback", metavar="NAME", help="Rollback a specific migration")
    parser.add_argument("--db-path", help="Override database path")
    parser.add_argument("--force", action="store_true", help="Force apply (skip checks)")
    
    args = parser.parse_args()
    
    db_path = args.db_path or get_db_path()
    
    print("""
╔══════════════════════════════════════════════╗
║        Zenvort Migration Runner             ║
╚══════════════════════════════════════════════╝
""")
    
    try:
        if args.status:
            show_status(db_path)
            
        elif args.rollback:
            conn = sqlite3.connect(db_path)
            ensure_migrations_table(conn)
            success = rollback_migration(conn, args.rollback)
            conn.close()
            if success:
                print(f"\n✅ Rolled back: {args.rollback}")
            sys.exit(0 if success else 1)
            
        else:
            applied = run_migrations(db_path, dry_run=args.dry_run)
            sys.exit(0 if applied >= 0 else 1)
            
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()