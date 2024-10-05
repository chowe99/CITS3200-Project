import sqlite3
conn = sqlite3.connect('soil_test_results.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE added_columns (id INTEGER PRIMARY KEY AUTOINCREMENT);''')

conn.commit()