# app/__init__.py
from flask import Flask
from app.blueprints.main import main  # Import the main blueprint

def create_app():
    app = Flask(__name__)

    # Configuration settings can be added here, e.g., app.config['SECRET_KEY'] = 'your_secret_key'

    # Register blueprints
    app.register_blueprint(main)

    return app
