# app/database/models.py

from sqlalchemy.dialects.sqlite import JSON
from .connection import db

class Spreadsheet(db.Model):
    __tablename__ = 'spreadsheets'
    spreadsheet_id = db.Column(db.Integer, primary_key=True)
    spreadsheet_name = db.Column(db.String, nullable=False, unique=True)
    public = db.Column(db.Boolean, default=True)
    encrypted = db.Column(db.Boolean, default=False)
    # Store the encrypted key, salt, and IV
    key_salt = db.Column(db.LargeBinary, nullable=True)
    iv = db.Column(db.LargeBinary, nullable=True)
    password_salt = db.Column(db.LargeBinary, nullable=True)  # Add this line
    password_hash = db.Column(db.LargeBinary, nullable=True)
    rows = db.relationship('SpreadsheetRow', backref='spreadsheet', lazy=True)
    instances = db.relationship(
        'Instance',
        secondary='spreadsheet_instances',
        backref=db.backref('spreadsheets', lazy='dynamic')
    )

class SpreadsheetRow(db.Model):
    __tablename__ = 'spreadsheet_rows'
    id = db.Column(db.Integer, primary_key=True)
    spreadsheet_id = db.Column(db.Integer, db.ForeignKey('spreadsheets.spreadsheet_id'), nullable=False)
    time_start_of_stage = db.Column(db.Text)
    shear_induced_PWP = db.Column(db.Text)
    axial_strain = db.Column(db.Text)
    vol_strain = db.Column(db.Text)
    induced_PWP = db.Column(db.Text)
    p = db.Column(db.Text)
    q = db.Column(db.Text)
    e = db.Column(db.Text)
    extra_data = db.Column(JSON)  # Add this line

class Instance(db.Model):
    __tablename__ = 'instances'
    instance_id = db.Column(db.Integer, primary_key=True)
    instance_name = db.Column(db.String, nullable=False)
    instance_value = db.Column(db.String, nullable=False)

class SpreadsheetInstance(db.Model):
    __tablename__ = 'spreadsheet_instances'
    id = db.Column(db.Integer, primary_key=True)
    spreadsheet_id = db.Column(db.Integer, db.ForeignKey('spreadsheets.spreadsheet_id'), nullable=False)
    instance_id = db.Column(db.Integer, db.ForeignKey('instances.instance_id'), nullable=False)

