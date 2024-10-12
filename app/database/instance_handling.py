# app/database/instance_handling.py

from .models import Instance, SpreadsheetInstance, Spreadsheet
from .connection import db
import pandas as pd

import logging
logger = logging.getLogger(__name__)

def find_instances(file):
    instances = {}

    try:
        # Read the '01 - Inputs' sheet without headers
        df = pd.read_excel(file, sheet_name='01 - Inputs', header=None)
    except Exception as e:
        logger.error(f"Error reading '01 - Inputs' sheet: {e}")
        return instances  # Return empty dict if sheet is missing

    try:
        # Extract names and values from C40:C47 and D40:D47
        names = df.iloc[39:47, 2].tolist()  # Column C (index 2)
        values = df.iloc[39:47, 3].tolist()  # Column D (index 3)
    except Exception as e:
        logger.error(f"Error extracting names and values: {e}")
        return instances

    for name, value in zip(names, values):
        if pd.notnull(name) and pd.notnull(value):
            instances[str(name).strip()] = str(value).strip()

    # Handle 'anisotropy' special case
    try:
        if df.shape[0] > 6:
            anisotropy_indicator = df.iloc[6, 3]  # Cell D7
            if anisotropy_indicator == 'from 0.3 - 1.0':
                anisotropy_value = df.iloc[6, 4]  # Cell E7
                if pd.notnull(anisotropy_value):
                    instances['anisotropy'] = str(anisotropy_value).strip()
    except Exception as e:
        logger.error(f"Error extracting anisotropy: {e}")

    return instances

def insert_instances_to_db(name, instances):
    try:
        for instance_name, instance_value in instances.items():
            # Fetch or create the Instance object
            instance_obj = Instance.query.filter_by(
                instance_name=instance_name,
                instance_value=instance_value
            ).first()

            if not instance_obj:
                instance_obj = Instance(
                    instance_name=instance_name,
                    instance_value=instance_value
                )
                db.session.add(instance_obj)
                logger.debug(f"Added new instance: {instance_name} - {instance_value}")

            # Create association with Spreadsheet
            spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=name).first()
            if spreadsheet:
                association = SpreadsheetInstance(
                    spreadsheet_id=spreadsheet.spreadsheet_id,
                    instance_id=instance_obj.instance_id
                )
                db.session.add(association)
                logger.debug(f"Associated instance '{instance_name} - {instance_value}' with spreadsheet '{name}'.")
            else:
                logger.error(f"Spreadsheet '{name}' not found for associating instances.")

        # Do NOT commit here
        logger.debug(f"Instances inserted for spreadsheet: {name}")

    except Exception as e:
        logger.exception(f"Error inserting instances into the database: {e}")
        raise  # Propagate exception to handle it in the calling function

