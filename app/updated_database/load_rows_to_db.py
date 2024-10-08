import sqlite3
import os
from app.updated_database.row_extractor import data_extractor

DATABASE_PATH = 'app/updated_database/soil_test_results.db'

conn = sqlite3.connect('soil_test_results.db')
cursor = conn.cursor()

def insert_data_to_db(doc_name, sheet_name, df):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    name = os.path.basename(doc_name).rsplit('.', 1)[0]
    cursor.execute('''INSERT INTO spreadsheets (spreadsheet_name) VALUES (?)''', (name,))
    spreadsheet_id = cursor.lastrowid

    for _, row in df.iterrows():
        cursor.execute('''
        INSERT INTO spreadsheet_rows (spreadsheet_id, time_start_of_stage, shear_induced_PWP, axial_strain, vol_strain, induced_PWP, p, q, e)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            spreadsheet_id,
            row['time_start_of_stage'],
            row['shear_induced_PWP'],
            row['axial_strain'],
            row['vol_strain'],
            row['induced_PWP'],
            row['p'],
            row['q'],
            row['e']
        ))
    conn.commit()
    conn.close()

