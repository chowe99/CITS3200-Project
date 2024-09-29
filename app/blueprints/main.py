# app/blueprints/main.py
import logging
from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
import csv

# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)  # Set logging level to debug
DEBUG = True  # Toggle this to enable or disable debugging print statements

def debug_print(message):
    """Prints debug messages if DEBUG is enabled."""
    if DEBUG:
        logging.debug(message)  # Use logging to print debug messages

main = Blueprint('main', __name__)

DATABASE_PATH = 'app/database/data.db'


def get_tables():
    """Retrieve all table names from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = [row[0] for row in conn.execute(query).fetchall()]
    conn.close()
    debug_print(f"Available tables: {tables}")
    return tables

def get_columns(table_name):
    """Retrieve column names from the selected table."""
    conn = sqlite3.connect(DATABASE_PATH)
    query = f"SELECT * FROM {table_name} LIMIT 1"
    df = pd.read_sql_query(query, conn)
    conn.close()
    debug_print(f"Columns in table '{table_name}': {df.columns.tolist()}")
    return df.columns.tolist()

@main.route('/')
def home():
    # Get all available tables from the database
    tables = get_tables()
    return render_template('home.html', tables=tables)

@main.route('/load-table', methods=['POST'])
def load_table():
    table_name = request.form['table_name']
    debug_print(f"Loading table: {table_name}")

    try:
        # Fetch column names based on the selected table
        columns = get_columns(table_name)

        # Define potential X-axis options (e.g., time columns, axial strain, mean effective stress)
        x_axis_options = [
            col for col in columns if "time_start_of_stage" in col or "Sec" in col or 
            "hours" in col or "axial_strain" in col or "axial strain" in col or 
            "p'" in col or "Mean Effective Stress" in col
        ]

        # Define potential Y-axis options (e.g., pressures, displacements, volumes, strains)
        y_axis_options = [
            col for col in columns if col not in x_axis_options
        ]

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
        table_name = request.form.get('table_name')
        x_axis = request.form.get('x_axis')
        y_axis = request.form.getlist('y_axis')

        if not table_name:
            debug_print("Table name is missing from the request.")
            return jsonify({"error": "Table name is missing from the request."}), 400

        if not x_axis:
            debug_print("X-axis field is missing from the request.")
            return jsonify({"error": "X-axis field is missing from the request."}), 400

        debug_print(f"Plotting from table: {table_name}, X-axis: {x_axis}, Y-axis: {y_axis}")

        # Check if Y-axis columns are selected
        if not y_axis:
            return jsonify({"error": "Please select at least one column for the Y-axis."})

        # Query the selected X and Y-axis columns from the user-selected table
        conn = sqlite3.connect(DATABASE_PATH)
        query = f"SELECT {x_axis}, {', '.join(y_axis)} FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        debug_print(f"Data retrieved for plotting: {df.head()}")

        # Generate plot
        plt.figure(figsize=(10, 6))
        for y in y_axis:
            plt.plot(df[x_axis], df[y], marker='o', label=y)
        plt.xlabel(x_axis)
        plt.ylabel(', '.join(y_axis))
        plt.title('User-Generated Plot')
        plt.legend()

        # Save plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        # Convert to base64 to send directly in the JSON response
        plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
        plot_url = f"data:image/png;base64,{plot_url}"

        # Return the plot URL as a JSON response
        return jsonify({"plot_url": plot_url})
    except Exception as e:
        debug_print(f"Error during plotting: {str(e)}")
        return jsonify({"error": f"Error during plotting: {str(e)}"}), 500


@main.route('/add-column', methods=['POST'])
def add_column():
    column_name = request.form['column_name']
    column_type = request.form['column_type']
    column_data = request.form.get('column_data', '')
    table_name = request.form.get('table_name', '')
    file = request.files.get('column_file')

    # Validate column name and type
    if not column_name or not column_type:
        return jsonify({"message": "Column name and type are required.", "success": False})
    if not table_name:
        return jsonify({"message": "Please load a table first.", "success": False})

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
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

        # Insert data into the new column
        for i, value in enumerate(data_list):
            conn.execute(f"UPDATE {table_name} SET {column_name} = ? WHERE rowid = ?", (value, i + 1))

        conn.commit()
        return jsonify({"message": f"Column '{column_name}' added successfully!", "success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Error adding column: {str(e)}", "success": False})
    finally:
        conn.close()

