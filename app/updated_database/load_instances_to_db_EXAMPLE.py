import sqlite3
from instances_extractor import find_instances

## This script isnt flexible for other spreadsheets

db = sqlite3.connect('soil_test_results.db')
cursor = db.cursor()

data = find_instances('Copy of CSL_1_U-template.xlsx')

def get_index(instance_name, instance_value, table_name):
    query = f"SELECT instance_id FROM {table_name} WHERE instance_name = ? AND instance_value = ?"
    cursor.execute(query, (instance_name, instance_value))
    result = cursor.fetchone()
    return result[0] if result else None

new = {}

name = 'CSL_1_U'
name_query = "SELECT spreadsheet_id FROM spreadsheets WHERE spreadsheet_name = ?"
cursor.execute(name_query, (name,))
name_result = cursor.fetchone()
value_list = name_result[0]

new['spreadsheet_id'] = value_list

for key in data:
    if key == "availability":
        if data[key] == "public":
            boolean_value = 1 ## One for true
        else:
            boolean_value = 0 ## Zero for false
        availability_query = "UPDATE spreadsheets SET public = ? WHERE spreadsheet_name = ?"
        cursor.execute(availability_query, (boolean_value, name))

    else: 
        index = get_index(key, data[key], 'instances')
        if index:
            new[key] = index
        else:
            new[key] = data[key]


columns = ', '.join(new.keys())
placeholders = ', '.join(f':{key}' for key in new.keys())

insert_query = f"INSERT INTO spreadsheet_instances ({columns}) VALUES ({placeholders})"
cursor.execute(insert_query, new)

db.commit()
db.close()