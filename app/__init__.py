"""
Main App
"""

import os
import logging
import smtplib
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from config import Config
from flask_user.signals import user_sent_invitation, user_registered
from .services.cache_service import init_cache, preload_popular_pages


db = SQLAlchemy()
migrate = Migrate()
bootstrap = Bootstrap()

def create_app(config_class=Config):
    app = Flask(__name__, subdomain_matching=True)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app)
    bootstrap.init_app(app)
    init_cache(app)

    # Import and initialize EmailService here to avoid circular imports
    from .services.email_service import EmailService
    email_service = EmailService(app)

    from .blueprints.main import bp as main_bp
    app.register_blueprint(main_bp)

    from .blueprints.cart import bp as cart_bp
    app.register_blueprint(cart_bp, url_prefix='/cart')

    from .blueprints.checkout import bp as checkout_bp
    app.register_blueprint(checkout_bp, url_prefix='/checkout')

    if not app.debug and not app.testing:
        if not os.path.exists(app.config['LOG_DIR']):
            os.mkdir(app.config['LOG_DIR'])
        file_handler = TimedRotatingFileHandler(app.config['LOG_DIR'] + '/locoganga.log', when='midnight', backupCount=30)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.debug('Locoganga startup')
    
    # Preload popular pages into cache
    @app.before_first_request
    def preload_cache():
        app.logger.info("Starting cache preloading")
        preload_popular_pages(app, pages=[1, 2, 3, 4, 5])

    return app
