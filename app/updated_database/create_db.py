import sqlite3

conn = sqlite3.connect('soil_test_results.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE spreadsheets (
    spreadsheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    spreadsheet_name TEXT NOT NULL
);
''')   

cursor.execute('''              
CREATE TABLE spreadsheet_rows (
    spreadsheet_id INTEGER,
    time_start_of_stage INTEGER,
    shear_induced_PWP REAL,
    axial_strain REAL,
    vol_strain REAL,
    induced_PWP  REAL,
    p REAL,
    q REAL,
    e REAL, 
    FOREIGN KEY (spreadsheet_id) REFERENCES spreadsheets(spreadsheet_id)
);
''')                       

conn.commit()
conn.close()