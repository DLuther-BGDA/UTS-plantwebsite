from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import os and sys for path manipulation
import os
import sys

# Add your project's root directory to the Python path.
# This ensures that imports like 'extensions', 'models', 'User' can be found.
# Assuming your 'alembic' directory is directly inside your project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import your SQLAlchemy 'db' instance from your Flask application.
# This assumes 'extensions.py' is in your project's root directory
# and contains your Flask-SQLAlchemy 'db' object.
try:
    from extensions import db
    # IMPORTANT: Import your models here so Alembic can discover them
    # and populate db.metadata.
    import models
    import User # Assuming User.py is also at the project root level
except ImportError as e:
    # This block is for debugging if imports fail again.
    # It will print more context about the import path.
    print(f"Error importing 'db' or models: {e}", file=sys.stderr)
    print(f"Current sys.path: {sys.path}", file=sys.stderr)
    print("Please ensure 'extensions.py', 'models.py', and 'User.py' are in your project root or accessible via sys.path.", file=sys.stderr)
    sys.exit(1)


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Set target_metadata to the metadata of your SQLAlchemy declarative base or db instance.
# For Flask-SQLAlchemy, this is typically db.metadata.
# Now that models and User have been imported, db.metadata should be fully populated.
target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Prefer DATABASE_URL environment variable for Docker/production environments.
    # This allows different database connections (local vs. deployed) without
    # modifying alembic.ini.
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        # Fallback to the URL specified in alembic.ini if the environment variable
        # is not set. This is useful for local development outside Docker,
        # or if alembic.ini still needs to define a default.
        db_url = config.get_main_option("sqlalchemy.url")

    # If you still want to explicitly use other sqlalchemy options from alembic.ini
    # besides the URL, you would merge them here.
    # For now, we're just passing the URL directly.
    connectable = engine_from_config(
        {"sqlalchemy.url": db_url}, # Pass the URL directly here
        prefix="sqlalchemy.",       # Still use prefix for other SQLAlchemy options if any are read
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
