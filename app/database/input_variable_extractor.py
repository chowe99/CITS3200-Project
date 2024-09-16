import openpyxl
import pandas as pd

def find_inputs_and_extract(doc_name, sheet_name, input_header):
    wb = openpyxl.load_workbook(doc_name)
    sheet = wb[sheet_name]
    
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value == input_header:
                column_value = cell.column
                row_value = cell.row
                break
    
    df = pd.read_excel(doc_name, sheet_name = sheet_name, header= row_value-1)
    wanted_columns = df.iloc[:, [column_value - 1, column_value, column_value + 1]]
    df_cleaned = wanted_columns.dropna(subset=[wanted_columns.columns[0]])

    result_dict = {}

    for _, row in df_cleaned.iterrows():
        if pd.notna(row[2]):
            result_dict[row.iloc[0]] = (row.iloc[1], row.iloc[2]) 
        else:
            result_dict[row.iloc[0]] = row.iloc[1]
    
    return result_dict
    
#print(find_inputs_and_extract('Copy of CSL_1_U-template.xlsx', '01 - Inputs', 'General inputs and calculations'))
#print(find_inputs_and_extract('Copy of CSL_1_U-template.xlsx', '01 - Inputs', 'Sample dimensions'))