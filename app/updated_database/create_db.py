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

cursor.execute('''
CREATE TABLE instances (
    instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_name TEXT NOT NULL,
    instance_value VAR NOT NULL                    
);
''')

cursor.execute('''
INSERT INTO instances (instance_name, instance_value)
VALUES
    ('drainage', 'drained'),
    ('drainage', 'undrained'),
    ('shearing', 'compression'),
    ('shearing', 'extension'),
    ('anisotropy', 'isotropic'),
    ('anisotropy', 'anisotropic'),
    ('availability', 'public'),
    ('availability', 'confidential'),
    ('density', 'loose'),
    ('density', 'dense'),
    ('plasticity', 'plastic'),
    ('plasticity', 'non-plastic'),
    ('plasticity', 'unknown'),
    ('PSD', 'clay'),
    ('PSD', 'silt'),
    ('PSD', 'sand')
''')

cursor.execute('''
CREATE TABLE spreadsheet_instances (
    spreadsheet_id INTEGER,
    drainage INTEGER,
    shearing INTEGER,
    anisotropy INTEGER,
    anisotropy_value INTEGER,
    consolidation INTEGER,
    availability INTEGER,
    density INTEGER,
    plasticity INTEGER,
    PSD INTEGER,
    
    FOREIGN KEY (spreadsheet_id) REFERENCES spreadsheets(spreadsheet_id)
    FOREIGN KEY (drainage) REFERENCES instances(instance_id),
    FOREIGN KEY (shearing) REFERENCES instances(instance_id),
    FOREIGN KEY (anisotropy) REFERENCES instances(instance_id),
    FOREIGN KEY (availability) REFERENCES instances(instance_id),
    FOREIGN KEY (density) REFERENCES instances(instance_id),
    FOREIGN KEY (plasticity) REFERENCES instances(instance_id),
    FOREIGN KEY (PSD) REFERENCES instances(instance_id)
);
''')

conn.commit()
conn.close()
