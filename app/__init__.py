"""
Main App
"""

import os
import logging
import smtplib
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request, current_app, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from config import Config
from flask_login import LoginManager
from flask_mail import Mail
from flask_session import Session

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
bootstrap = Bootstrap()
mail = Mail()
sess = Session()  # Renamed to avoid conflict with Flask's session

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    sess.init_app(app)  # Initialize Flask-Session

    # Configure login manager
    login.login_view = 'auth.login'
    login.login_message = 'Please log in to access this page.'

    # Register blueprints
    from .blueprints import products, cart, orders, payments, auth, main
    app.register_blueprint(products.bp)
    app.register_blueprint(cart.bp, url_prefix='/cart')
    app.register_blueprint(orders.bp, url_prefix='/orders')
    app.register_blueprint(payments.bp, url_prefix='/payments')
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(main.bp)

    # Create necessary directories
    os.makedirs(app.config['LOG_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Create database tables
    with app.app_context():
        db.create_all()

    @app.before_request
    def before_request():
        """Ensure session is initialized"""
        if 'session_id' not in session:
            import hashlib
            from datetime import datetime
            session['session_id'] = hashlib.md5(
                str(datetime.now().timestamp()).encode()
            ).hexdigest()

    @app.after_request
    def after_request(response):
        """Add CORS headers"""
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
        return response

    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists(app.config['LOG_DIR']):
            os.mkdir(app.config['LOG_DIR'])
        file_handler = TimedRotatingFileHandler(
            os.path.join(app.config['LOG_DIR'], 'locoganga.log'),
            when='midnight',
            backupCount=30
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Locoganga startup')

    return app
