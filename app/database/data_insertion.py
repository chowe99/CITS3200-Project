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
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = PKCS7(128).padder()
    padded_data = padder.update(value.encode()) + padder.finalize()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(encrypted).decode('utf-8')

def insert_data_to_db(name, df, spreadsheet=None, encrypt=False, encryption_key=None, iv=None, retries=3, delay=2):
    for attempt in range(retries):
        try:
            if spreadsheet is None:
                existing_spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=name).first()
                if existing_spreadsheet:
                    return {'success': False, 'message': 'Spreadsheet already exists in the database.'}

                spreadsheet = Spreadsheet(spreadsheet_name=name, encrypted=encrypt)
                db.session.add(spreadsheet)
                db.session.flush()  # Flush to assign spreadsheet_id

            rows = []
            for _, row in df.iterrows():
                data = {}
                for column in df.columns:
                    value = str(row[column]) if pd.notnull(row[column]) else ''
                    if encrypt:
                        data[column] = encrypt_value(value, encryption_key, iv)
                    else:
                        data[column] = value

                row_entry = SpreadsheetRow(
                    spreadsheet_id=int(spreadsheet.spreadsheet_id),
                    **data
                )
                rows.append(row_entry)
            db.session.bulk_save_objects(rows)
            # Removed commit here; transaction is managed externally
            return {'success': True, 'message': 'Data inserted successfully.'}
        
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"OperationalError on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                logger.info(f"Retrying after {delay} seconds...")
                time.sleep(delay)
                continue
            else:
                return {'success': False, 'message': 'Database I/O error. Please try again later.'}
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return {'success': False, 'message': 'An unexpected error occurred.'}

