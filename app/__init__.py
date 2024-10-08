from flask import Flask
from app.blueprints.main import main
from app.database import db
from flask_migrate import Migrate
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'

    # Configure the database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@db:5432/yourdb')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)

    # Register blueprints
    app.register_blueprint(main)

    return app

