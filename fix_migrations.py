#!/usr/bin/env python
"""
Script to fix Flask-Migrate environment and ensure migrations work correctly
"""
import os
import sys
import shutil

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def fix_env_py():
    """Fix the migrations/env.py file to work with current Flask-Migrate"""
    env_py_path = os.path.join(os.path.dirname(__file__), 'migrations', 'env.py')
    
    if not os.path.exists(env_py_path):
        print(f"❌ Error: {env_py_path} does not exist")
        return False
    
    # Create a backup
    backup_path = env_py_path + '.bak'
    shutil.copy2(env_py_path, backup_path)
    print(f"✅ Created backup of env.py at {backup_path}")
    
    # Read the current env.py file
    with open(env_py_path, 'r') as f:
        env_py_content = f.read()
    
    # Replace the problematic get_engine functions with a more robust version
    updated_content = """
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

def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


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
        url=url, target_metadata=get_metadata(), literal_binds=True
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

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            process_revision_directives=process_revision_directives,
            **current_app.extensions['migrate'].configure_args
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
    
    print(f"✅ Updated {env_py_path} with more robust engine handling")
    return True

def ensure_migrations_dir():
    """Ensure migrations directory exists and is properly initialized"""
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    
    if not os.path.exists(migrations_dir):
        print(f"❌ Migrations directory does not exist at {migrations_dir}")
        print("Creating migrations directory...")
        
        # Import and initialize the app
        from app import create_app, db
        app = create_app()
        
        with app.app_context():
            from flask_migrate import Migrate, init
            migrate = Migrate(app, db)
            init()
            print(f"✅ Initialized migrations directory at {migrations_dir}")
    else:
        print(f"✅ Migrations directory exists at {migrations_dir}")
    
    # Check for versions directory
    versions_dir = os.path.join(migrations_dir, 'versions')
    if not os.path.exists(versions_dir):
        os.makedirs(versions_dir)
        print(f"✅ Created versions directory at {versions_dir}")
    else:
        print(f"✅ Versions directory exists at {versions_dir}")
    
    return True

def create_migration():
    """Create a migration for the WinitProduct table"""
    # Import the app
    from app import create_app, db
    app = create_app()
    
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import WinitProduct
        
        # Create the migration
        from flask_migrate import Migrate, migrate as create_migration
        migrate = Migrate(app, db)
        
        print("Creating migration for WinitProduct table...")
        create_migration(message='add_winit_products_table')
        print("✅ Migration created successfully")
        
        # Ask to apply migration
        apply_now = input("Do you want to apply the migration now? (y/n): ")
        if apply_now.lower() == 'y':
            from flask_migrate import upgrade
            print("Applying migration...")
            upgrade()
            print("✅ Migration applied successfully")
            
            # Verify table was created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'winit_products' in inspector.get_table_names():
                print("✅ WinitProduct table was created in the database")
            else:
                print("❌ WinitProduct table was not created in the database")
    
    return True

def main():
    try:
        print("Fixing Flask-Migrate environment...")
        
        # 1. Ensure migrations directory exists
        if not ensure_migrations_dir():
            print("❌ Failed to ensure migrations directory exists")
            return
        
        # 2. Fix the env.py file
        if not fix_env_py():
            print("❌ Failed to fix env.py file")
            return
        
        # 3. Create migration for WinitProduct
        if not create_migration():
            print("❌ Failed to create migration")
            return
        
        print("\n✅ Migration environment fixed successfully!")
        print("You should now be able to use 'flask db migrate' and 'flask db upgrade' commands.")
        
    except Exception as e:
        print(f"❌ Error fixing migration environment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 