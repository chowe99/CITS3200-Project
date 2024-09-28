import pandas as pd

def data_extractor(doc_name, sheet):

    read_df = pd.read_excel(doc_name, sheet_name= sheet, header=[10, 11])

    selected_columns = [
        ('Time start of stage ', '(Sec)'), 
        ('Shear induced PWP', 'Unnamed: 23_level_1'), 
        ('Shear induced PWP', 'Axial strain'), 
        ('Shear induced PWP', 'Vol strain'),
        ('Shear induced PWP', 'Induced PWP'), 
        ('Shear induced PWP', "p'"),
        ('Shear induced PWP', 'q'), 
        ('Shear induced PWP', 'e')]

    df = read_df[selected_columns]

    df.columns = ['_'.join(col) for col in df.columns.values]
    df.columns = ['time_start_of_stage', 'shear_induced_PWP', 'axial_strain', 'vol_strain', 'induced_PWP', "p", 'q', 'e']
    df.loc[df['axial_strain'] < 0, 'axial_strain'] = 0
    df = df.round(2)

    return df


