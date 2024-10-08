# app/database/data_insertion.py

from .models import Spreadsheet, SpreadsheetRow
from .connection import db
import pandas as pd

def insert_data_to_db(name, df):
    """Insert data into the database."""
    # Check if the spreadsheet already exists
    existing_spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=name).first()
    if existing_spreadsheet:
        return {'success': False, 'message': 'Spreadsheet already exists in the database.'}

    spreadsheet = Spreadsheet(spreadsheet_name=name)
    db.session.add(spreadsheet)
    db.session.commit()

    rows = []
    for _, row in df.iterrows():
        row_entry = SpreadsheetRow(
            spreadsheet_id=int(spreadsheet.spreadsheet_id),
            time_start_of_stage=float(row['time_start_of_stage']) if pd.notnull(row['time_start_of_stage']) else None,
            shear_induced_PWP=float(row['shear_induced_PWP']) if pd.notnull(row['shear_induced_PWP']) else None,
            axial_strain=float(row['axial_strain']) if pd.notnull(row['axial_strain']) else None,
            vol_strain=float(row['vol_strain']) if pd.notnull(row['vol_strain']) else None,
            induced_PWP=float(row['induced_PWP']) if pd.notnull(row['induced_PWP']) else None,
            p=float(row['p']) if pd.notnull(row['p']) else None,
            q=float(row['q']) if pd.notnull(row['q']) else None,
            e=float(row['e']) if pd.notnull(row['e']) else None
        )
        rows.append(row_entry)
    db.session.bulk_save_objects(rows)
    db.session.commit()
    return {'success': True, 'message': 'Data inserted successfully.'}

