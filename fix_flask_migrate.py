#!/usr/bin/env python
"""
Script to fix Flask-Migrate by explicitly setting the database URL
"""
import os
import sys
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in environment variables")
    sys.exit(1)

print(f"Using database URL: {DATABASE_URL}")

def fix_env_py():
    """Fix the migrations/env.py file by explicitly setting the database URL"""
    env_py_path = os.path.join(os.path.dirname(__file__), 'migrations', 'env.py')
    
    if not os.path.exists(env_py_path):
        print(f"❌ Error: {env_py_path} does not exist")
        return False
    
    # Create a backup
    backup_path = env_py_path + '.bak'
    shutil.copy2(env_py_path, backup_path)
    print(f"✅ Created backup of env.py at {backup_path}")
    
    # Create a new env.py file with explicit database URL
    updated_content = f"""
import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Set the database URL explicitly
config.set_main_option('sqlalchemy.url', '{DATABASE_URL}')

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from flask import current_app
target_metadata = current_app.extensions['migrate'].db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    \"\"\"Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    \"\"\"
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    \"\"\"Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    \"\"\"
    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    # Create the engine directly
    from sqlalchemy import engine_from_config, pool
    
    # Use the explicitly set URL
    alembic_config = config.get_section(config.config_ini_section)
    alembic_config['sqlalchemy.url'] = config.get_main_option('sqlalchemy.url')
    
    # Create the engine
    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
    
    # Write the updated content
    with open(env_py_path, 'w') as f:
        f.write(updated_content)
    
    print(f"✅ Updated {env_py_path} with explicit database URL")
    return True

def main():
    try:
        print("Fixing Flask-Migrate environment...")
        
        # Fix the env.py file
        if not fix_env_py():
            print("❌ Failed to fix env.py file")
            return
        
        print("\n✅ Migration environment fixed successfully!")
        print("You should now be able to use 'flask db migrate' and 'flask db upgrade' commands.")
        print("\nNext steps:")
        print("1. Run 'flask db migrate -m \"add winit products table\"'")
        print("2. Run 'flask db upgrade'")
        print("3. Run 'python import_winit_products.py' to import products")
        
    except Exception as e:
        print(f"❌ Error fixing migration environment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 