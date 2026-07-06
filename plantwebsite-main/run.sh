#!/bin/sh
# run.sh

echo "Waiting for PostgreSQL..."

# Loop until the PostgreSQL database is ready using pg_isready
# This now uses the DATABASE_URL environment variable, which contains
# the full connection string (including hostname, port, and user for Render).
# pg_isready (PostgreSQL 10+ clients) can directly understand the URL.
while ! pg_isready -d "$DATABASE_URL" > /dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1 # Wait for 1 second before retrying
done

echo "PostgreSQL is up - running database setup script..."

# Execute the Python script responsible for creating/checking database tables.
# This ensures your database schema is up-to-date.
python db_setup.py

echo "All database tables created/checked."

# Start Gunicorn, the production-ready WSGI HTTP Server for Python web applications.
# '__init__:app' specifies the Flask application instance 'app' found in the '__init__.py' module.
# '-b 0.0.0.0:"$PORT"' tells Gunicorn to bind to all network interfaces on the port
# provided by Render's $PORT environment variable. This is essential for Render
# to detect and route traffic to your application.
# 'exec' replaces the current shell process with the gunicorn process,
# ensuring signals (like SIGTERM for graceful shutdown) are correctly handled by Gunicorn.
exec gunicorn __init__:app -b 0.0.0.0:"$PORT"
