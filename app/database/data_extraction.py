# app/database/data_extraction.py

import pandas as pd
import logging

logger = logging.getLogger(__name__)

def data_extractor(file, sheet):
    try:
        logger.debug(f"Attempting to read sheet '{sheet}' from file '{file.filename}'.")
        read_df = pd.read_excel(file, sheet_name=sheet, header=[10, 11])
        logger.debug(f"Successfully read sheet '{sheet}'. Shape: {read_df.shape}")

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
        logger.debug(f"Selected columns: {selected_columns}. Shape after selection: {df.shape}")

        df.columns = ['_'.join(col).strip() for col in df.columns.values]
        df.columns = ['time_start_of_stage', 'shear_induced_PWP', 'axial_strain', 'vol_strain',
                      'induced_PWP', "p", 'q', 'e']
        logger.debug(f"Renamed columns to: {df.columns.tolist()}")

        # Replace negative axial_strain with 0
        negative_strains = df['axial_strain'] < 0
        num_negative = negative_strains.sum()
        if num_negative > 0:
            logger.warning(f"Found {num_negative} rows with negative 'axial_strain'. Replacing with 0.")
            df.loc[negative_strains, 'axial_strain'] = 0

        # Drop rows where all selected columns are NaN
        initial_rows = df.shape[0]
        df = df.dropna(subset=df.columns, how='all')
        dropped_rows = initial_rows - df.shape[0]
        if dropped_rows > 0:
            logger.warning(f"Dropped {dropped_rows} rows where all selected columns are NaN.")

        # Additional validation: Ensure required columns are present
        required_columns = ['time_start_of_stage', 'shear_induced_PWP', 'axial_strain', 'vol_strain', 'induced_PWP', "p", 'q', 'e']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return pd.DataFrame()

        # Ensure data types are correct
        for col in ['time_start_of_stage', 'shear_induced_PWP', 'axial_strain', 'vol_strain', 'induced_PWP', "p", 'q', 'e']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            num_non_numeric = df[col].isna().sum()
            if num_non_numeric > 0:
                logger.warning(f"Column '{col}' has {num_non_numeric} non-numeric entries coerced to NaN.")

        logger.info(f"Data extraction successful. Final DataFrame shape: {df.shape}")
        return df

    except Exception as e:
        # Log the error with stack trace and return an empty DataFrame
        logger.exception(f"Error extracting data from sheet '{sheet}': {e}")
        return pd.DataFrame()

