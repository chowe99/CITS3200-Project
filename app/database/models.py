# app/database/models.py

from .connection import db

class Spreadsheet(db.Model):
    __tablename__ = 'spreadsheets'
    spreadsheet_id = db.Column(db.Integer, primary_key=True)
    spreadsheet_name = db.Column(db.String, nullable=False, unique=True)
    public = db.Column(db.Boolean, default=True)
    rows = db.relationship('SpreadsheetRow', backref='spreadsheet', lazy=True)
    instances = db.relationship('SpreadsheetInstance', backref='spreadsheet', lazy=True)

class SpreadsheetRow(db.Model):
    __tablename__ = 'spreadsheet_rows'
    id = db.Column(db.Integer, primary_key=True)
    spreadsheet_id = db.Column(db.Integer, db.ForeignKey('spreadsheets.spreadsheet_id'), nullable=False)
    time_start_of_stage = db.Column(db.Float)
    shear_induced_PWP = db.Column(db.Float)
    axial_strain = db.Column(db.Float)
    vol_strain = db.Column(db.Float)
    induced_PWP = db.Column(db.Float)
    p = db.Column(db.Float)
    q = db.Column(db.Float)
    e = db.Column(db.Float)

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
    # Define columns dynamically as needed

