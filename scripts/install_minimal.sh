#!/bin/bash

# Minimal installation script for Locoganga

echo "Installing minimal required packages for Locoganga..."

# Core Flask packages
pip install Flask==2.0.3 Werkzeug==2.0.3
pip install Flask-Login==0.5.0
pip install Flask-User==1.0.2.2
pip install Flask-WTF==0.15.1
pip install Flask-Mail==0.9.1
pip install Flask-SQLAlchemy==2.5.1
pip install Flask-Migrate==4.0.7
pip install Flask-Bootstrap==3.3.7.1

# Database
pip install SQLAlchemy==1.4.46
pip install alembic==1.9.4
pip install mysqlclient==2.1.1

# Utilities
pip install python-dotenv==1.0.0
pip install requests==2.28.2
pip install stripe==5.2.0

# Web server
pip install gunicorn==20.1.0

echo "Installation complete. You can now start the application." 