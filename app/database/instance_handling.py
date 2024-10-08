# app/database/instance_handling.py

from .models import Instance, SpreadsheetInstance, Spreadsheet
from .connection import db
import pandas as pd

def find_instances(file):
    instances = {}

    try:
        # Read the '01 - Inputs' sheet without headers
        df = pd.read_excel(file, sheet_name='01 - Inputs', header=None)

        # Extract names and values from C40:C47 and D40:D47
        names = df.iloc[39:47, 2].tolist()  # Column C (index 2)
        values = df.iloc[39:47, 3].tolist()  # Column D (index 3)

        for name, value in zip(names, values):
            if pd.notnull(name) and pd.notnull(value):
                instances[str(name).strip()] = str(value).strip()

        # Handle 'anisotropy' special case
        if df.shape[0] > 6:
            anisotropy_indicator = df.iloc[6, 3]  # Cell D7
            if anisotropy_indicator == 'from 0.3 - 1.0':
                anisotropy_value = df.iloc[6, 4]  # Cell E7
                if pd.notnull(anisotropy_value):
                    instances['anisotropy'] = str(anisotropy_value).strip()
    except Exception as e:
        # Log the error and proceed without instance data
        logger.debug(f"Error extracting instances: {str(e)}")

    return instances

def insert_instances_to_db(spreadsheet_name, instances_data):
    spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=spreadsheet_name).first()
    if not spreadsheet:
        return {'success': False, 'message': 'Spreadsheet not found.'}

    for key, value in instances_data.items():
        # Check if the instance already exists
        instance = Instance.query.filter_by(instance_name=key, instance_value=value).first()
        if not instance:
            instance = Instance(instance_name=key, instance_value=value)
            db.session.add(instance)
            db.session.commit()

        # Create a link between the spreadsheet and the instance
        existing_link = SpreadsheetInstance.query.filter_by(
            spreadsheet_id=spreadsheet.spreadsheet_id,
            instance_id=instance.instance_id
        ).first()

        if not existing_link:
            spreadsheet_instance = SpreadsheetInstance(
                spreadsheet_id=spreadsheet.spreadsheet_id,
                instance_id=instance.instance_id
            )
            db.session.add(spreadsheet_instance)
    db.session.commit()
    return {'success': True, 'message': 'Instances inserted successfully.'}

