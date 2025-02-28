"""
Config file for app
"""
import os
import sys
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    USER_APP_NAME = "LOCOGANGA"
    USER_ENABLE_USERNAME = False
    USER_ENABLE_EMAIL = True
    USER_REQUIRE_INVITATION = True
    USER_ENABLE_INVITE_USER = True
    CSRF_ENABLED = True
    SERVER_NAME = os.environ.get('SERVER_NAME') or 'locoganga.com'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024
    ROOT_DIRECTORY = os.path.dirname(__file__)

    LOG_DIR = os.path.join(ROOT_DIRECTORY, 'logs')

    # Stripe configuration
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    DOMAIN_URL = os.environ.get('DOMAIN_URL', 'http://localhost:5000')

    # Winit API configuration
    WINIT_API_URL = os.environ.get('WINIT_API_URL', 'https://openapi.wanyilian.com/cedpopenapi/service')
    WINIT_APP_KEY = os.environ.get('WINIT_APP_KEY')
    WINIT_TOKEN = os.environ.get('WINIT_TOKEN')

    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Product settings
    PRODUCT_PAGE_SIZE = int(os.environ.get('PRODUCT_PAGE_SIZE', 20))  # Products per page
