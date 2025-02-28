#!/bin/bash

# Script to fix Flask version compatibility issues

echo "Fixing Flask version compatibility issues..."

# Deactivate virtual environment if active
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "Deactivating current virtual environment..."
    deactivate
fi

# Create a backup of the current environment
echo "Creating backup of current packages..."
pip freeze > requirements.backup.txt

# Install compatible versions
echo "Installing compatible versions of Flask and extensions..."
pip install Flask==2.0.3 Werkzeug==2.0.3 --force-reinstall
pip install Flask-Login==0.5.0 --force-reinstall
pip install Flask-User==1.0.2.2 --force-reinstall
pip install Flask-WTF==0.15.1 --force-reinstall
pip install Flask-SQLAlchemy==2.5.1 --force-reinstall
pip install SQLAlchemy==1.4.46 --force-reinstall

echo "Installation complete. Please restart your application."
echo "If you encounter issues, you can restore your previous environment with:"
echo "pip install -r requirements.backup.txt --force-reinstall" 