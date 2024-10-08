# app/database/models.py

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
    instances = db.relationship('SpreadsheetInstance', backref='spreadsheet', lazy=True)

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

class Instance(db.Model):
    __tablename__ = 'instances'
    instance_id = db.Column(db.Integer, primary_key=True)
    instance_name = db.Column(db.String, nullable=False)
    instance_value = db.Column(db.String, nullable=False)
    spreadsheet_instances = db.relationship('SpreadsheetInstance', backref='instance', lazy=True)

class SpreadsheetInstance(db.Model):
    __tablename__ = 'spreadsheet_instances'
    id = db.Column(db.Integer, primary_key=True)
    spreadsheet_id = db.Column(db.Integer, db.ForeignKey('spreadsheets.spreadsheet_id'), nullable=False)
    instance_id = db.Column(db.Integer, db.ForeignKey('instances.instance_id'), nullable=False)

class AddedColumn(db.Model):
    __tablename__ = 'added_columns'
    id = db.Column(db.Integer, primary_key=True)
    # Existing columns
    # New columns can be stored as key-value pairs or JSON

class AddedColumnData(db.Model):
    __tablename__ = 'added_column_data'
    id = db.Column(db.Integer, primary_key=True)
    added_column_id = db.Column(db.Integer, db.ForeignKey('added_columns.id'), nullable=False)
    column_name = db.Column(db.String, nullable=False)
    value = db.Column(db.String)  # Or use appropriate data type
