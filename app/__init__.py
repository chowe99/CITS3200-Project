import os
from flask import Flask
from app.blueprints.main import main
from app.database import db

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'

    # Use the database at /mnt/nas/soil_test_results.db
    db_path = os.environ.get('DATABASE_PATH', '/mnt/nas/soil_test_results.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()  # Create tables if they don't exist

    return app

