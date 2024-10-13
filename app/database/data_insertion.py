# app/database/data_insertion.py

from .models import Spreadsheet, SpreadsheetRow
from .connection import db
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
import base64

import pandas as pd
import time
import sqlalchemy.exc
import logging

logger = logging.getLogger(__name__)

def encrypt_value(value, key, iv):
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        padder = PKCS7(128).padder()
        padded_data = padder.update(value.encode()) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        logger.exception(f"Error encrypting value '{value}': {e}")
        raise  # Re-raise exception after logging

def insert_data_to_db(name, df, spreadsheet=None, encrypt=False, encryption_key=None, iv=None, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        try:
            if spreadsheet is None:
                existing_spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=name).first()
                if existing_spreadsheet:
                    logger.warning(f"Spreadsheet '{name}' already exists in the database.")
                    return {'success': False, 'message': 'Spreadsheet already exists in the database.'}

                spreadsheet = Spreadsheet(spreadsheet_name=name, encrypted=encrypt)
                db.session.add(spreadsheet)
                db.session.flush()  # Flush to assign spreadsheet_id
                if spreadsheet.spreadsheet_id is None:
                    logger.error(f"Failed to assign spreadsheet_id for '{name}'. The spreadsheet_id is None after flush.")
                    raise ValueError(f"Spreadsheet ID is None for '{name}'.")
                else:
                    logger.debug(f"Added Spreadsheet '{name}' with ID {spreadsheet.spreadsheet_id} to the session.")

            rows = []
            for idx, row in df.iterrows():
                data = {}
                for column in df.columns:
                    value = str(row[column]) if pd.notnull(row[column]) else ''
                    if encrypt:
                        data[column] = encrypt_value(value, encryption_key, iv)
                    else:
                        data[column] = value

                if spreadsheet.spreadsheet_id is None:
                    logger.error(f"Spreadsheet ID is None for '{name}'. Cannot insert rows.")
                    raise ValueError(f"Spreadsheet ID is None for '{name}'. Cannot insert rows.")

                row_entry = SpreadsheetRow(
                    spreadsheet_id=int(spreadsheet.spreadsheet_id),
                    **data
                )
                rows.append(row_entry)
                logger.debug(f"Prepared row for Spreadsheet '{name}': {data}")

            db.session.bulk_save_objects(rows)
            logger.info(f"Bulk saved {len(rows)} rows for Spreadsheet '{name}'.")

            # Do not commit here; let the caller handle it
            return {'success': True, 'message': 'Data inserted successfully.'}

        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"OperationalError on attempt {attempt} for Spreadsheet '{name}': {e}", exc_info=True)
            if attempt < retries:
                logger.info(f"Retrying to insert data for Spreadsheet '{name}' after {delay} seconds...")
                time.sleep(delay)
                continue
            else:
                logger.critical(f"Failed to insert data for Spreadsheet '{name}' after {retries} attempts.")
                return {'success': False, 'message': 'Database I/O error. Please try again later.'}
        except Exception as e:
            logger.exception(f"Unexpected error on attempt {attempt} for Spreadsheet '{name}': {e}")
            return {'success': False, 'message': 'An unexpected error occurred while inserting data.'}

