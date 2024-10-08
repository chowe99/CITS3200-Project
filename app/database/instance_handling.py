# app/database/instance_handling.py

from .models import Instance, SpreadsheetInstance, Spreadsheet
from .connection import db
import pandas as pd

def find_instances(file_path):
    # Implement instance extraction logic here
    pass

def insert_instances_to_db(spreadsheet_name, instances_data):
    spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=spreadsheet_name).first()
    if not spreadsheet:
        return {'success': False, 'message': 'Spreadsheet not found.'}

    for key, value in instances_data.items():
        instance = Instance.query.filter_by(instance_name=key, instance_value=value).first()
        if not instance:
            instance = Instance(instance_name=key, instance_value=value)
            db.session.add(instance)
            db.session.commit()

        spreadsheet_instance = SpreadsheetInstance(
            spreadsheet_id=spreadsheet.spreadsheet_id,
            instance_id=instance.instance_id
        )
        db.session.add(spreadsheet_instance)
    db.session.commit()
    return {'success': True, 'message': 'Instances inserted successfully.'}

