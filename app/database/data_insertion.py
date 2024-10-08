# app/database/data_insertion.py

from .models import Spreadsheet, SpreadsheetRow
from .connection import db
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
import base64

import pandas as pd

def encrypt_value(value, key, iv):
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = PKCS7(128).padder()
    padded_data = padder.update(value.encode()) + padder.finalize()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(encrypted).decode('utf-8')

def insert_data_to_db(name, df, spreadsheet=None, encrypt=False, encryption_key=None, iv=None):

    if spreadsheet is None:
        existing_spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=name).first()
        if existing_spreadsheet:
            return {'success': False, 'message': 'Spreadsheet already exists in the database.'}

        spreadsheet = Spreadsheet(spreadsheet_name=name, encrypted=encrypt)
        db.session.add(spreadsheet)
        db.session.commit()

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
    db.session.commit()
    return {'success': True, 'message': 'Data inserted successfully.'}

