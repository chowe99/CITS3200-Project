import sqlite3
from cleaning_script import data_extractor

conn = sqlite3.connect('soil_test_results.db')
cursor = conn.cursor()

def insert_data_to_db(doc_name, sheet_name):
    name = doc_name.rsplit('.', 1)[0]
    cursor.execute('''INSERT INTO spreadsheets (spreadsheet_name) VALUES (?)''', (name,))
    spreadsheet_id = cursor.lastrowid

    df = data_extractor(doc_name, sheet_name)

    for _, row in df.iterrows():
        cursor.execute('''
        INSERT INTO spreadsheet_rows (spreadsheet_id, time_start_of_stage, shear_induced_PWP, axial_strain, vol_strain, induced_PWP, p, q, e)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (spreadsheet_id, row['time_start_of_stage'], row['shear_induced_PWP'], row['axial_strain'], row['vol_strain'], row['induced_PWP'], row['p'], row['q'], row['e']))


spreadsheet_files = ['CSL_1_U.xlsx', 'CSL_2_U.xlsx', 'CSL_3_D.xlsx']
for file in spreadsheet_files:
    insert_data_to_db(file, '03 - Shearing')


conn.commit()
conn.close()