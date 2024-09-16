# app/blueprints/main.py
from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import io
import base64
import csv

main = Blueprint('main', __name__)

DATABASE_PATH = 'app/database/data.db'

@main.route('/')
def home():
    # Connect to database to get column names dynamically
    conn = sqlite3.connect(DATABASE_PATH)
    query = "SELECT * FROM CSL_1_U LIMIT 1"  # Adjust your table name here
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Extract column names
    columns = df.columns.tolist()

    # Define potential X-axis options (e.g., time columns)
    x_axis_options = [col for col in columns if "time_start_of_stage" in col or "Sec" in col or "hours" in col]

    # Define potential Y-axis options (e.g., pressure, volume, strain)
    y_axis_options = [col for col in columns if col not in x_axis_options]

    return render_template('home.html', columns=columns, x_axis_options=x_axis_options, y_axis_options=y_axis_options)

@main.route('/plot', methods=['POST'])
def plot():
    x_axis = request.form['x_axis']
    y_axis = request.form.getlist('y_axis')  # Get selected Y-axis columns

    # Check if Y-axis columns are selected
    if not y_axis:
        return jsonify({"error": "Please select at least one column for the Y-axis."})

    # Query the selected X and Y-axis columns from the database
    conn = sqlite3.connect(DATABASE_PATH)
    query = f"SELECT {x_axis}, {', '.join(y_axis)} FROM CSL_1_U"  # Adjust your table name
    df = pd.read_sql_query(query, conn)
    conn.close()

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
        conn.execute(f"ALTER TABLE CSL_1_U ADD COLUMN {column_name} {column_type}")

        # Insert data into the new column
        for i, value in enumerate(data_list):
            conn.execute(f"UPDATE CSL_1_U SET {column_name} = ? WHERE rowid = ?", (value, i + 1))

        conn.commit()
        return jsonify({"message": f"Column '{column_name}' added successfully!", "success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Error adding column: {str(e)}", "success": False})
    finally:
        conn.close()

