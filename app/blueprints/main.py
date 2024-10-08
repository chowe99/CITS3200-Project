# app/blueprints/main.py
import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.database import (
    data_extractor,
    insert_data_to_db,
    find_instances,
    insert_instances_to_db,
    get_tables,
    get_instances,
    get_columns,
    Spreadsheet,
    SpreadsheetRow,
)
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

# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)  # Set logging level to debug
logger = logging.getLogger(__name__)


main = Blueprint('main', __name__)

DATABASE_PATH = 'app/database/soil_test_results.db'

ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/upload', methods=['POST'])
def upload_file():
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request.'})
    file = request.files['excel_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        sheet_name = '03 - Shearing'  # Adjust as necessary
        df = data_extractor(file, sheet_name)
        name = filename.rsplit('.', 1)[0]
        result = insert_data_to_db(name, df)
        if result['success']:
            # Optionally, handle instances
            instances_data = find_instances(file)
            if instances_data:
                insert_instances_to_db(name, instances_data)
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']})
    else:
        return jsonify({'success': False, 'message': 'Invalid file type. Only .xlsx files are allowed.'})

@main.route('/')
def home():
    # Get all available tables from the database
    tables = get_tables()
    instances = get_instances()
    return render_template('home.html', tables=tables, instances = instances)

@main.route('/load-table', methods=['POST']) #load columns
def load_table():
    table_name = request.form.getlist('table_name[]')
    logger.debug(f"Loading table: {table_name}")

    try:
        # Fetch column
        columns = get_columns()

        # Define potential X-axis options (e.g., time columns, axial strain, mean effective stress)
        x_axis_options = [col for col in columns if col != "spreadsheet_id"]
        y_axis_options = [col for col in columns if col != "spreadsheet_id" and col != "time_start_of_stage" and col != "id"]

        # Define potential Y-axis options (e.g., pressures, displacements, volumes, strains)

        logger.debug(f"X-axis options: {x_axis_options}")
        logger.debug(f"Y-axis options: {y_axis_options}")

        return jsonify({
            "success": True,
            "x_axis_options": x_axis_options,
            "y_axis_options": y_axis_options
        })

    except Exception as e:
        logger.debug(f"Error loading table: {str(e)}")
        return jsonify({"success": False, "message": f"Error loading table: {str(e)}"})

@main.route('/get-tables', methods=['GET'])
def get_tables_endpoint():
    tables = get_tables()
    return jsonify({'tables': tables})

@main.route('/plot', methods=['POST'])
def plot():
    try:
        table_names = request.form.getlist('table_name[]')
        x_axis = request.form.get('x_axis')
        y_axis = request.form.getlist('y_axis')

        if not table_names:
            return jsonify({"error": "Table name is missing from the request."}), 400

        if not x_axis:
            return jsonify({"error": "X-axis field is missing from the request."}), 400

        if not y_axis:
            return jsonify({"error": "Please select at least one column for the Y-axis."}), 400

        # Fetch data using SQLAlchemy
        data_frames = []
        for table_name in table_names:
            spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=table_name).first()
            if not spreadsheet:
                continue
            rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()
            if not rows:
                continue
            # Convert rows to DataFrame
            df = pd.DataFrame([row.__dict__ for row in rows])
            df['source'] = table_name
            data_frames.append(df)

        if not data_frames:
            return jsonify({"error": "No data found for the selected tables."}), 404

        # Combine data from all selected tables
        data = pd.concat(data_frames, ignore_index=True)

        # Create a Plotly figure
        fig = go.Figure()

        for y in y_axis:
            if y in data.columns:
                fig.add_trace(go.Scatter(
                    x=data[x_axis],
                    y=data[y],
                    mode='markers+lines',
                    name=f"{y}",
                    text=data['source'],
                    hovertemplate=(
                        f"<b>{y}</b>: %{{y}}<br>"
                        f"<b>{x_axis}</b>: %{{x}}<br>"
                        f"<b>Spreadsheet</b>: %{{text}}<br>"
                        "<extra></extra>"
                    )
                ))
            else:
                continue

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

