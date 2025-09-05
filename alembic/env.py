import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add your app directory to sys.path (so Alembic can import your models)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 🔁 Adjust this import to point to your models file
from models import Base  # If you use declarative_base()
# from database import db  # Uncomment if you use Flask-SQLAlchemy style

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 🔁 Use appropriate metadata depending on your setup
target_metadata = Base.metadata
# target_metadata = db.Model.metadata  # For Flask-SQLAlchemy

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
