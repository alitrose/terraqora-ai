from logging.config import fileConfig
import os
from pathlib import Path
import sys
from alembic import context
from sqlalchemy import pool

# Ensure backend/ is importable regardless of working directory
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import _normalize_database_url, get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import build_engine  # noqa: E402
import app.models  # noqa: E402, F401  -- registers all 11 ORM models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    override = config.get_main_option("sqlalchemy.url")
    if override:
        return _normalize_database_url(override)
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return _normalize_database_url(env_url)
    get_settings.cache_clear()
    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_database_url()
    connectable = build_engine(url)

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
