# app/database/instance_handling.py

from .models import Instance, SpreadsheetInstance, Spreadsheet
from .connection import db
import pandas as pd

import logging
logger = logging.getLogger(__name__)

def find_instances(file):
    instances = {}

    try:
        logger.debug(f"Attempting to read '01 - Inputs' sheet from file '{file.filename}'.")
        df = pd.read_excel(file, sheet_name='01 - Inputs', header=None)
        logger.debug(f"Successfully read '01 - Inputs' sheet. Shape: {df.shape}")
    except Exception as e:
        logger.exception(f"Error reading '01 - Inputs' sheet: {e}")
        return instances  # Return empty dict if sheet is missing

    try:
        # Extract names and values from C40:C47 and D40:D47
        names = df.iloc[39:47, 2].tolist()  # Column C (index 2)
        values = df.iloc[39:47, 3].tolist()  # Column D (index 3)
        logger.debug(f"Extracted {len(names)} names and {len(values)} values from '01 - Inputs' sheet.")
    except Exception as e:
        logger.exception(f"Error extracting names and values: {e}")
        return instances

    for name, value in zip(names, values):
        if pd.notnull(name) and pd.notnull(value):
            instances[str(name).strip()] = str(value).strip()
            logger.debug(f"Found instance: {name} = {value}")

    # Handle 'anisotropy' special case
    try:
        if df.shape[0] > 6:
            anisotropy_indicator = df.iloc[6, 3]  # Cell D7
            if anisotropy_indicator == 'from 0.3 - 1.0':
                anisotropy_value = df.iloc[6, 4]  # Cell E7
                if pd.notnull(anisotropy_value):
                    instances['anisotropy'] = str(anisotropy_value).strip()
                    logger.debug(f"Found anisotropy instance: anisotropy = {anisotropy_value}")
    except Exception as e:
        logger.exception(f"Error extracting anisotropy: {e}")

    logger.info(f"Total instances found: {len(instances)}")
    return instances

def insert_instances_to_db(name, instances):
    if not instances:
        logger.warning(f"No instances to insert for Spreadsheet '{name}'.")
        return

    try:
        spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=name).first()
        if not spreadsheet:
            logger.error(f"Spreadsheet '{name}' not found in the database.")
            return

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
                logger.debug(f"Added new Instance: {instance_name} = {instance_value}")

            # Check if association already exists
            association = SpreadsheetInstance.query.filter_by(
                spreadsheet_id=spreadsheet.spreadsheet_id,
                instance_id=instance_obj.instance_id
            ).first()

            if not association:
                association = SpreadsheetInstance(
                    spreadsheet_id=spreadsheet.spreadsheet_id,
                    instance_id=instance_obj.instance_id
                )
                db.session.add(association)
                logger.debug(f"Associated Instance '{instance_name} = {instance_value}' with Spreadsheet '{name}'.")
            else:
                logger.debug(f"Association already exists for Instance '{instance_name} = {instance_value}' with Spreadsheet '{name}'.")

        logger.info(f"All instances for Spreadsheet '{name}' have been processed and added to the session.")

    except Exception as e:
        logger.exception(f"Error inserting instances into the database for Spreadsheet '{name}': {e}")
        raise  # Propagate exception to handle it in the calling function

