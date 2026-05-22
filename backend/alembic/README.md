# Database Migrations with Alembic

This directory contains Alembic database migrations for the Ground Station application.

## Overview

The Ground Station uses Alembic for database schema migrations. This ensures that:
- Users can upgrade to new versions without losing data
- Database schema changes are versioned and tracked
- Migrations run automatically when the Docker container starts

## Automatic Migrations

**For end users**: No action required! When you start the Ground Station container, migrations run automatically during startup. Your database will be automatically upgraded to the latest schema version.

## For Developers

### Creating a New Migration

When you modify the database models in `db/models.py`, you need to create a migration:

```bash
cd /path/to/backend
source venv/bin/activate
python run_alembic.py revision --autogenerate -m "Description of changes"
```

This will:
1. Compare your models with the current database schema
2. Generate a migration file in `alembic/versions/`
3. The migration will be automatically applied on next startup

**Note**: Review the generated migration carefully! Autogenerate may detect spurious changes (e.g., UUID vs NUMERIC in SQLite). Edit the migration file to remove any unnecessary changes before committing.

### Example Workflow

Here's a complete example of adding a new field to the database:

```bash
# 1. Modify db/models.py (e.g., add a field to Satellites model)
# 2. Navigate to backend directory
cd /path/to/backend
source venv/bin/activate

# 3. Generate migration
python run_alembic.py revision --autogenerate -m "Add description field to satellites"

# 4. Review the generated migration file
# Open alembic/versions/xxxx_add_description_field_to_satellites.py
# Remove any spurious changes (like UUID vs NUMERIC)

# 5. Test the migration
python run_alembic.py upgrade head

# 6. If successful, commit the migration file
git add alembic/versions/xxxx_add_description_field_to_satellites.py
git commit -m "Add description field to satellites table"
```

### Manual Migration Commands

Useful commands for managing migrations:

```bash
# Show current database version
python run_alembic.py current

# Show migration history
python run_alembic.py history

# Upgrade to latest version
python run_alembic.py upgrade head

# Downgrade one version
python run_alembic.py downgrade -1

# Create empty migration (for data migrations)
python run_alembic.py revision -m "Populate default values"
```

### Migration File Location

Migration files are stored in: `backend/alembic/versions/`

Each migration file contains:
- `upgrade()`: SQL commands to apply the migration
- `downgrade()`: SQL commands to rollback the migration

### Environment Variables

- `GS_DB`: Override the database filename (default: `gs.db`)
- `ALEMBIC_CONTEXT`: Set to `1` to prevent argument parsing conflicts

## How It Works

1. **On Container Startup**: The `startup.sh` script starts the application
2. **In `app.py`**: The `init_db()` function is called
3. **Migration Runner**: `db/migrations.py` runs all pending migrations
4. **Alembic**: Applies any new migrations to bring schema up to date
5. **Application Starts**: Once migrations complete, the app starts normally

## Technical Details

### SQLite Support

The migrations are configured with `render_as_batch=True` to support SQLite's limited ALTER TABLE capabilities.

### Async Support

The migration system works with SQLAlchemy's async engine using:
- `async_engine_from_config()` for database connections
- `run_sync()` to execute synchronous migration code
- ThreadPoolExecutor to avoid event loop conflicts

### Argument Handling

The `common/arguments.py` module checks for `ALEMBIC_CONTEXT` environment variable to avoid parsing Alembic's command-line arguments as application arguments.

## Troubleshooting

### "No such table: alembic_version"

This is normal for a fresh database. The table will be created on first migration.

### Migration Fails

Check the logs for specific errors. Common issues:
- Database file permissions
- Disk space
- Conflicting schema changes

### Reset Database (Development Only)

To start fresh (⚠️ **destroys all data**):

```bash
rm data/gs.db
# Restart the application - it will recreate and migrate
```

## What to Commit to Git

**Always commit:**
- ✅ `alembic.ini`
- ✅ `alembic/env.py`
- ✅ `alembic/script.py.mako`
- ✅ `alembic/README.md`
- ✅ `alembic/versions/*.py` (all migration files)
- ✅ `run_alembic.py`
- ✅ `db/migrations.py`

**Never commit:**
- ❌ `alembic/__pycache__/`
- ❌ `alembic/versions/__pycache__/`
- ❌ `data/*.db` (database files)
- ❌ `data/*.db.backup`

## Migration Best Practices

1. **Test migrations** on a copy of your database first
2. **Backup** your database before upgrading in production
3. **Review generated migrations** - auto-generate isn't perfect
4. **One logical change** per migration
5. **Descriptive messages** - help future developers understand changes
6. **Always commit migration files** - they are part of your codebase

## File Structure

```
backend/
├── alembic/
│   ├── versions/           # Migration files
│   │   └── xxx_description.py
│   ├── env.py             # Alembic environment config
│   ├── script.py.mako     # Template for new migrations
│   └── README.md          # This file
├── alembic.ini            # Alembic configuration
├── db/
│   ├── models.py          # SQLAlchemy models
│   └── migrations.py      # Migration runner utility
└── run_alembic.py         # Wrapper script for alembic CLI
```
