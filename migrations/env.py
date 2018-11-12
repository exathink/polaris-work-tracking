from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

import os

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support



from polaris.utils.config import get_config_provider
# Update this to the correct path to package where the model lives.
from polaris.work_tracking.db import model
target_metadata = model.Base.metadata


def include_schemas(names):
    # produce an include object function that filters on the given schemas
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table":
            return object.schema in names
        return True
    return include_object


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_config_provider().get('POLARIS_DB_URL')
    if url is None:
        raise EnvironmentError("Could not load POLARIS_DB_URL from config provider")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        literal_binds=True,
        version_table='alembic_version',
        version_table_schema=target_metadata.schema
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        {'sqlalchemy.url': get_config_provider().get('POLARIS_DB_URL')},
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_schemas([target_metadata.schema]),
            version_table='alembic_version',
            version_table_schema=target_metadata.schema
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
