import pandas as pd
import warnings

## The following function searches 'Drainage' and 'Shearing' in each sheet and extracts instances from sheet into a dictionary
def find_instances(file_path):
    read_doc = pd.ExcelFile(file_path)
    
    for sheet in read_doc.sheet_names:
        df = pd.read_excel(read_doc, sheet_name=sheet)
        result = df[df.isin(["Drainage"])]
        cell_location = result.stack().index.tolist()

        if cell_location:
            for loc in cell_location:
                row_index, col_index = loc
                col_index = int(col_index) if isinstance(col_index, (int, float)) else df.columns.get_loc(col_index) # Avoid value error

                value_below_cell = df.iloc[row_index + 1, col_index]
                if value_below_cell == "Shearing":
                
## Following section puts instances in dictionary
                    
                    data_dict = {}
            
                    for i in range(row_index, len(df)):
                        key = df.iloc[i, col_index]          
                        value = df.iloc[i, col_index + 1]   
                        anisotropy_value = df.iloc[i, col_index + 2] if pd.notna(df.iloc[i, col_index + 2]) else None 
                        
                        data_dict[key] = value
                        if anisotropy_value:
                            data_dict ['anisotropy_value'] = anisotropy_value
                    
                    new_dict = {}
                    
                    for key in data_dict:
                        if key == 'PSD':
                            new_dict['PSD'] = data_dict['PSD']
                        elif key == 'Consolidation (10-1000)':
                            new_dict['consolidation'] = data_dict[key]
                        else:
                            new_dict[key.lower()] = data_dict[key]
                    
                    return new_dict
                            
                        
#find_instances('Copy of CSL_1_U-template.xlsx')
