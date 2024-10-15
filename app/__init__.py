# app/__init__.py

import os
import logging
from flask import Flask
from app.blueprints.main import main
from app.database import db

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'

    # Centralized Logging Configuration
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for detailed logs; change to INFO or WARNING in production
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Flask application.")


    # Specify the folder path
    folder_path = '//drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735'

    # List all files in the specified folder
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file():
                    app.logger.debug(entry.name)
    except FileNotFoundError:
        app.logger.debug(f"The folder '{folder_path}' does not exist.")


    # Use the DATABASE_PATH environment variable
    db_path = os.getenv('DATABASE_PATH', 'sqlite:///soil_tests.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Replace backslashes with forward slashes for SQLite URI compatibility
    db_path = db_path.replace('\\', '/')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()  # Create tables if they don't exist
            # Integrity Check
        try:
            from sqlalchemy import text
            result = db.session.execute(text("PRAGMA integrity_check;")).fetchone()
            if result[0] == "ok":
                logger.info("Database integrity check passed.")
            else:
                logger.error(f"Database integrity check failed: {result[0]}")
        except Exception as e:
            logger.exception(f"Failed to perform database integrity check: {e}")

    return app

