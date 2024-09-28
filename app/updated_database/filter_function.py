import sqlite3
import pandas as pd

def get_index(filter_type, filter_list): # (string, list)
    db = sqlite3.connect('soil_test_results.db')
    cursor = db.cursor()
    
    quoted_list = [f'"{item}"' for item in filter_list]
    filters = ', '.join(quoted_list)
    
    if filter_type == "spreadsheets":
        cursor.execute(f"SELECT spreadsheet_id FROM spreadsheets WHERE spreadsheet_name IN ({filters})")
        result = cursor.fetchall()
        indexes = [str(item[0]) for item in result]
        
    elif filter_type == "instances":
        cursor.execute(f"SELECT instance_name, instance_id FROM instances WHERE instance_value IN ({filters})")
        result = cursor.fetchall()
        dictionary = dict(result)
        indexes = {key: str(value) for key, value in dictionary.items()}
    
    db.close()
    return indexes

## Tests
#print(get_index("spreadsheets", ['CSL_1_U', 'CSL_2_U']))
#print(get_index("instances", ['drained', 'isotropic']))


def data_filter(filter_type, filter_list, columns): # (string, list, list)
    indexes = get_index(filter_type, filter_list)
    
    joined_columns = ', '.join(columns)
    
    print(joined_columns)
    
    db = sqlite3.connect('soil_test_results.db')
    
    if filter_type == "spreadsheets": #indexes is a list
        joined_indexes = ', '.join(indexes)
        query = f"SELECT {joined_columns} FROM spreadsheet_rows WHERE spreadsheet_id IN ({joined_indexes})"

    elif filter_type == "instances": #indexes is a dictionary
        print(indexes)
        index = []
        for key in indexes:
            string = "spreadsheet_instances." + key + " == " + indexes[key]
            index.append(string)
        joined_indexes = ' AND '.join(index)
        query = f"SELECT {joined_columns} FROM spreadsheet_rows JOIN spreadsheet_instances ON spreadsheet_rows.spreadsheet_id = spreadsheet_instances.spreadsheet_id WHERE {joined_indexes}"
    
    df = pd.read_sql_query(query, db)
    db.close()
    return df
    
## Tests
#print(data_filter("spreadsheets", ['CSL_1_U', 'CSL_2_U'], ['axial_strain']))
#print(data_filter("instances", ['drained', 'isotropic'], ['axial_strain', 'p']))
    

## Add plot examples