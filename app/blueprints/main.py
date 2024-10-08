# app/blueprints/main.py
import logging
from app.updated_database.load_rows_to_db import insert_data_to_db
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import pandas as pd
import sqlite3
import plotly
import plotly.graph_objs as go
import io
import base64
import csv
import json
import os
from werkzeug.utils import secure_filename
from app.updated_database.row_extractor import data_extractor
from app.updated_database.load_rows_to_db import insert_data_to_db





# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)  # Set logging level to debug
DEBUG = True  # Toggle this to enable or disable debugging print statements

def debug_print(message):
    """Prints debug messages if DEBUG is enabled."""
    if DEBUG:
        logging.debug(message)  # Use logging to print debug messages

main = Blueprint('main', __name__)

DATABASE_PATH = 'app/updated_database/soil_test_results.db'

UPLOAD_FOLDER = 'uploads'  
ALLOWED_EXTENSIONS = {'xlsx'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_uploaded_file(file_path):
    try:
        sheet_name = '03 - Shearing'  # Adjust as necessary
        df = data_extractor(file_path, sheet_name)
        if df.empty:
            debug_print(f"No data found in file {file_path}.")
            flash('Uploaded file contains no data.')
            return
        # Check for existing spreadsheet
        name = os.path.basename(file_path).rsplit('.', 1)[0]
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM spreadsheets WHERE spreadsheet_name = ?', (name,))
        if cursor.fetchone()[0] > 0:
            debug_print(f"Spreadsheet {name} already exists in the database.")
            flash('Spreadsheet already exists in the database.')
            conn.close()
            return
        conn.close()
        # Insert data
        insert_data_to_db(file_path, sheet_name, df)
        debug_print(f"Data from {file_path} has been inserted into the database.")
        flash('File processed and data added to the database.')
    except Exception as e:
        debug_print(f"Error processing file {file_path}: {str(e)}")
        flash(f'Error processing file: {str(e)}')


@main.route('/upload', methods=['POST'])
def upload_file():
    if 'excel_file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['excel_file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        debug_print(f"File uploaded successfully: {file_path}")
        # Process the uploaded file
        process_uploaded_file(file_path)
        flash('File processed and data added to the database.')
        return redirect(url_for('main.home'))
    else:
        flash('Invalid file type. Only .xlsx files are allowed.')
        return redirect(request.url)

def get_tables():
    """Retrieve all table names from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    query = "SELECT spreadsheet_name FROM spreadsheets;"
    tables = [row[0] for row in conn.execute(query).fetchall()]
    conn.close()
    debug_print(f"Available tables: {tables}")
    return tables

def get_instances():
    conn = sqlite3.connect(DATABASE_PATH)
    query = "SELECT instance_name, instance_value FROM instances;"
    result = conn.execute(query).fetchall()
    instances = {}

    for row in result:
        key = row[0]
        value = row[1]
        if key in instances:
            instances[key].append(value)
        else:
            instances[key] = [value]
    
    conn.close()
    debug_print(f"Available instances: {instances}")
    return instances

def get_columns():
    """Retrieve column names from the table structure."""
    conn = sqlite3.connect(DATABASE_PATH)
    query = f"SELECT * FROM spreadsheet_rows, added_columns LIMIT 1"
    df = pd.read_sql_query(query, conn)
    
    conn.close()
    debug_print(f"Columns available: {df.columns.tolist()}")
    return df.columns.tolist()

@main.route('/')
def home():
    # Get all available tables from the database
    tables = get_tables()
    instances = get_instances()
    return render_template('home.html', tables=tables, instances = instances)

@main.route('/load-table', methods=['POST']) #load columns
def load_table():
    table_name = request.form.getlist('table_name[]')
    debug_print(f"Loading table: {table_name}")

    try:
        # Fetch column
        columns = get_columns()

        # Define potential X-axis options (e.g., time columns, axial strain, mean effective stress)
        x_axis_options = [col for col in columns if col != "spreadsheet_id"]
        y_axis_options = [col for col in columns if col != "spreadsheet_id" and col != "time_start_of_stage" and col != "id"]

        # Define potential Y-axis options (e.g., pressures, displacements, volumes, strains)

        debug_print(f"X-axis options: {x_axis_options}")
        debug_print(f"Y-axis options: {y_axis_options}")

        return jsonify({
            "success": True,
            "x_axis_options": x_axis_options,
            "y_axis_options": y_axis_options
        })

    except Exception as e:
        debug_print(f"Error loading table: {str(e)}")
        return jsonify({"success": False, "message": f"Error loading table: {str(e)}"})


@main.route('/plot', methods=['POST'])
def plot():
    try:
        table_names = request.form.getlist('table_name[]')
        x_axis = request.form.get('x_axis')
        y_axis = request.form.getlist('y_axis')

        if not table_names:
            debug_print("Table name is missing from the request.")
            return jsonify({"error": "Table name is missing from the request."}), 400

        if not x_axis:
            debug_print("X-axis field is missing from the request.")
            return jsonify({"error": "X-axis field is missing from the request."}), 400

        if not y_axis:
            return jsonify({"error": "Please select at least one column for the Y-axis."}), 400

        debug_print(f"Plotting from tables: {table_names}, X-axis: {x_axis}, Y-axis: {y_axis}")

        conn = sqlite3.connect(DATABASE_PATH)

        # Get the list of unadded columns from spreadsheet_rows
        df_temp = pd.read_sql_query("SELECT * FROM spreadsheet_rows LIMIT 1", conn)
        unadded_columns = df_temp.columns.tolist()

        # Separate Y-axis variables into unadded and added
        selected_unadded_y = [item for item in y_axis if item in unadded_columns]
        selected_added_y = [item for item in y_axis if item not in unadded_columns]

        data_frames = []
        for table in table_names:
            # Fetch data for unadded columns
            columns_to_select = [x_axis] + selected_unadded_y
            query = f"""
                SELECT {', '.join(columns_to_select)}, spreadsheet_name
                FROM spreadsheet_rows
                JOIN spreadsheets ON spreadsheet_rows.spreadsheet_id = spreadsheets.spreadsheet_id
                WHERE spreadsheet_name = ?
            """
            df_unadded = pd.read_sql_query(query, conn, params=(table,))
            df_unadded['source'] = table  # Add a column to identify the data source

            # Fetch data for added columns
            if selected_added_y:
                added_columns_query = f"SELECT {', '.join(selected_added_y)} FROM added_columns"
                df_added = pd.read_sql_query(added_columns_query, conn)
                # Assuming that the number of rows in df_unadded and df_added are the same
                if len(df_unadded) != len(df_added):
                    # Handle mismatched lengths, possibly truncate or fill missing values
                    min_length = min(len(df_unadded), len(df_added))
                    df_unadded = df_unadded.iloc[:min_length]
                    df_added = df_added.iloc[:min_length]
                # Merge added columns into df_unadded
                df_unadded.reset_index(drop=True, inplace=True)
                df_added.reset_index(drop=True, inplace=True)
                df_combined = pd.concat([df_unadded, df_added], axis=1)
            else:
                df_combined = df_unadded

            data_frames.append(df_combined)

        conn.close()

        # Combine data from all selected tables
        if data_frames:
            data = pd.concat(data_frames, ignore_index=True)
        else:
            return jsonify({"error": "No data found for the selected tables."}), 404

        # Create a Plotly figure
        fig = go.Figure()

        # Plot unadded Y-axis variables
        if selected_unadded_y:
            for y in selected_unadded_y:
                fig.add_trace(go.Scatter(
                    x=data[x_axis],
                    y=data[y],
                    mode='markers+lines',
                    name=f"{y} (Original Data)",
                    text=data['source'],
                    hovertemplate=(
                        f"<b>{y}</b>: %{{y}}<br>"
                        f"<b>{x_axis}</b>: %{{x}}<br>"
                        f"<b>Spreadsheet</b>: %{{text}}<br>"
                        "<extra></extra>"
                    )
                ))

        # Plot added Y-axis variables
        if selected_added_y:
            for y in selected_added_y:
                if y in data.columns:
                    fig.add_trace(go.Scatter(
                        x=data[x_axis],
                        y=data[y],
                        mode='markers+lines',
                        name=f"{y} (Added Data)",
                        text=data['source'],
                        hovertemplate=(
                            f"<b>{y}</b>: %{{y}}<br>"
                            f"<b>{x_axis}</b>: %{{x}}<br>"
                            f"<b>Spreadsheet</b>: %{{text}}<br>"
                            "<extra></extra>"
                        )
                    ))
                else:
                    debug_print(f"Column {y} not found in data.")

        # Customize the layout
        fig.update_layout(
            title='Interactive Plot',
            xaxis_title=x_axis,
            yaxis_title=', '.join(y_axis),
            legend_title="Variables",
            hovermode='closest'
        )

        # Convert the figure to JSON
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return jsonify({"graph_json": graph_json})

    except Exception as e:
        debug_print(f"Error during plotting: {str(e)}")
        return jsonify({"error": f"Error during plotting: {str(e)}"}), 500

@main.route('/add-column', methods=['POST'])
def add_column():
    column_name = request.form['column_name']
    column_type = request.form['column_type']
    column_data = request.form.get('column_data', '')
    file = request.files.get('column_file')

    # Validate column name and type
    if not column_name or not column_type:
        return jsonify({"message": "Column name and type are required.", "success": False})

    # Prepare data from textarea or CSV file
    data_list = []
    if file:
        # Read data from uploaded CSV file
        file_data = file.read().decode('utf-8')
        reader = csv.reader(file_data.splitlines())
        data_list = [row[0] for row in reader]
    elif column_data:
        # Read data from the textarea, split by commas
        data_list = column_data.split(',')

    # Convert data to the appropriate type
    if column_type == 'INTEGER':
        data_list = [int(value) for value in data_list]
    elif column_type == 'REAL':
        data_list = [float(value) for value in data_list]
    else:
        data_list = [str(value) for value in data_list]

    # Add the new column to the database
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Add column to the table
        conn.execute(f"ALTER TABLE added_columns ADD COLUMN {column_name} {column_type}")

        # Insert data into the new column
        for i, value in enumerate(data_list):
            conn.execute(f"UPDATE added_columns SET {column_name} = ? WHERE rowid = ?", (value, i + 1))

        conn.commit()
        return jsonify({"message": f"Column '{column_name}' added successfully!", "success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Error adding column: {str(e)}", "success": False})
    finally:
        conn.close()

