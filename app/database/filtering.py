# app/database/filtering.py

from .models import Spreadsheet, Instance, SpreadsheetInstance, SpreadsheetRow
from .connection import db

def get_tables():
    """Retrieve all spreadsheet names from the database."""
    tables = Spreadsheet.query.with_entities(Spreadsheet.spreadsheet_name).all()
    return [table[0] for table in tables]

def get_instances():
    """Retrieve all instances from the database."""
    instances = Instance.query.all()
    instance_dict = {}
    for instance in instances:
        key = instance.instance_name
        value = instance.instance_value
        if key in instance_dict:
            instance_dict[key].append(value)
        else:
            instance_dict[key] = [value]
    return instance_dict

def get_columns():
    """Retrieve column names from the SpreadsheetRow model."""
    return [column.name for column in SpreadsheetRow.__table__.columns if column.name != 'id']

