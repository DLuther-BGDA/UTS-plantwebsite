import os
import sys
import time
import traceback
from sqlalchemy.exc import OperationalError

# Import your Flask app and db instance
from __init__ import app
from extensions import db

# Import all your models so SQLAlchemy knows about them for dropping/creating tables
from models import (
    ClientBusiness, DataSource, Family, LocalSpeciesInfo,
    Occurrence, Reserve, Species, SpeciesTraitJunction, Traits
)
from User import User

def wait_for_db(flask_app_instance, max_attempts=10, delay=2):
    """Waits for the PostgreSQL database connection to be ready."""
    with flask_app_instance.app_context():
        attempts = 0
        while attempts < max_attempts:
            try:
                # Try connecting to the default bind (PostgreSQL)
                db.session.execute(db.text('SELECT 1'))
                print("PostgreSQL is up and accessible.", file=sys.stdout)
                return True
            except OperationalError as e:
                print(f"PostgreSQL is unavailable - sleeping ({attempts+1}/{max_attempts}). Error: {e}", file=sys.stderr)
                time.sleep(delay)
                attempts += 1
        print("Failed to connect to PostgreSQL after multiple attempts.", file=sys.stderr)
        return False

def table_exists(db_instance, table_name):
    """Checks if a table exists in the connected database."""
    try:
        # For PostgreSQL, check information_schema
        result = db_instance.session.execute(
            db.text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                );
            """)
        ).scalar()
        return result
    except Exception as e:
        print(f"ERROR checking table existence for '{table_name}': {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

if __name__ == '__main__':
    print("--- Starting database setup script ---", file=sys.stdout)

    # Ensure the Flask app context is available
    with app.app_context():
        # First, ensure the PostgreSQL DB is up
        if not wait_for_db(app):
            print("Exiting db_setup.py: Could not connect to PostgreSQL.", file=sys.stderr)
            sys.exit(1)

        try:
            print("Checking if 'users' table exists BEFORE db.create_all()...", file=sys.stdout)
            users_table_exists_before = table_exists(db, 'users')
            print(f"'users' table exists before create_all: {users_table_exists_before}", file=sys.stdout)

            print("Attempting to create all missing tables (db.create_all())...", file=sys.stdout)
            # db.create_all() creates tables only if they don't already exist.
            # This should create the 'users' table if it's missing.
            db.create_all()
            print("db.create_all() completed.", file=sys.stdout)

            print("Checking if 'users' table exists AFTER db.create_all()...", file=sys.stdout)
            users_table_exists_after = table_exists(db, 'users')
            print(f"'users' table exists after create_all: {users_table_exists_after}", file=sys.stdout)

            if not users_table_exists_after:
                print("WARNING: 'users' table still does not exist after db.create_all(). This is unexpected. Manual intervention may be needed.", file=sys.stderr)
            else:
                print("'users' table successfully created or confirmed after db.create_all().", file=sys.stdout)



        except Exception as e:
            db.session.rollback() # Rollback any partial changes on error
            print(f"ERROR: An unhandled exception occurred during db_setup.py: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr) # Print full traceback for debugging
            sys.exit(1)
    print("--- Database setup script finished ---", file=sys.stdout)
