# wipe_db.py
# This script is used to completely reset the database:
# It drops all tables defined by SQLAlchemy models and then recreates them.
# This effectively wipes all data and resets the schema to its initial state.

import os
import sys
import time
from sqlalchemy.exc import OperationalError, ProgrammingError

# Import the Flask app and db instance
from __init__ import app
from extensions import db

# Import all SQLAlchemy models so db.drop_all() and db.create_all() can discover them.
from models import (
    ClientBusiness, DataSource, Family, LocalSpeciesInfo,
    Occurrence, Reserve, Species, SpeciesTraitJunction, Traits
)
from User import User

def wait_for_db(flask_app_instance, max_attempts=20, delay=2):
    """
    Waits for the PostgreSQL database connection to be ready.
    Retries connection attempts, handling common startup errors.
    """
    with flask_app_instance.app_context():
        attempts = 0
        while attempts < max_attempts:
            try:
                # Attempt a simple query to check database connectivity.
                db.session.execute(db.text('SELECT 1'))
                print("PostgreSQL is up and accessible.", file=sys.stdout)
                return True
            except (OperationalError, ProgrammingError) as e:
                # Catch both connection errors and early-stage programming errors (e.g., DB not fully initialized).
                print(f"PostgreSQL is unavailable or not fully ready - sleeping ({attempts+1}/{max_attempts}). Error: {e}", file=sys.stderr)
                time.sleep(delay)
                attempts += 1
        print("Failed to connect to PostgreSQL after multiple attempts.", file=sys.stderr)
        return False

if __name__ == '__main__':
    print("--- Starting database wipe and recreation script ---", file=sys.stdout)

    # Ensure the Flask application context is active for database operations.
    with app.app_context():
        # First, wait until the PostgreSQL database container is fully ready.
        if not wait_for_db(app):
            print("Exiting wipe_db.py: Could not establish connection to PostgreSQL.", file=sys.stderr)
            sys.exit(1)

        try:
            print("Attempting to drop all existing tables...", file=sys.stdout)
            # db.drop_all() drops tables for all registered models.
            db.drop_all()
            print("All tables dropped successfully (if they existed).", file=sys.stdout)

            print("Attempting to recreate all tables...", file=sys.stdout)
            db.create_all()
            print("All tables recreated successfully as empty tables.", file=sys.stdout)

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: An unhandled exception occurred during database wipe/recreation: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    print("--- Database wipe and recreation complete ---", file=sys.stdout)