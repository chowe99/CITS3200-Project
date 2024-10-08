# app/blueprints/main.py
import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, session
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
    db
)
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
import base64
import pandas as pd
import plotly
import plotly.graph_objs as go
import csv
import json
import os
from werkzeug.utils import secure_filename
import hashlib

# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)  # Set logging level to debug
logger = logging.getLogger(__name__)


main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def derive_key(password, salt):
    # Use PBKDF2HMAC to derive a key from the password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256 key size
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode())

def hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt, pwd_hash

def verify_password(stored_salt, stored_hash, password_attempt):
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password_attempt.encode(), stored_salt, 100000)
    return pwd_hash == stored_hash

@main.route('/upload', methods=['POST'])
def upload_file():
    password = request.form.get('encrypt_password')
    encrypt_data = bool(password)

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

        if encrypt_data:
            # Generate a random salt and IV
            salt = os.urandom(16)
            iv = os.urandom(16)
            key = derive_key(password, salt)

            # Hash the password for verification
            password_salt, password_hash = hash_password(password)

            # Store the encrypted data and metadata
            spreadsheet = Spreadsheet(
                spreadsheet_name=name,
                public=False,
                encrypted=True,
                key_salt=salt,
                iv=iv,
                password_salt=password_salt,
                password_hash=password_hash
            )
            db.session.add(spreadsheet)
            db.session.commit()

             # Pass the spreadsheet object to insert_data_to_db
            result = insert_data_to_db(
                name, df, spreadsheet=spreadsheet, encrypt=True, encryption_key=key, iv=iv
            )

            if result['success']:
                return jsonify({'success': True, 'message': 'Encrypted data inserted successfully.'})
            else:
                return jsonify({'success': False, 'message': result['message']})

        else:
            # Handle unencrypted data insertion
            result = insert_data_to_db(name, df)
            if result['success']:
                return jsonify({'success': True, 'message': result['message']})
            else:
                return jsonify({'success': False, 'message': result['message']})
    else:
        return jsonify({'success': False, 'message': 'Invalid file type. Only .xlsx files are allowed.'})

@main.route('/')
def home():
    try:
        # Get all available tables from the database
        tables = get_tables()
        instances = get_instances()
    except Exception as e:
        flash('Unable to connect to the database. Please ensure the NAS is mounted.', 'error')
        tables = []
        instances = {}
    return render_template('home.html', tables=tables, instances=instances)

@main.route('/load-table', methods=['POST'])
def load_table():
    table_names = request.form.getlist('table_name[]')
    password = request.form.get('decrypt_password')  

    # Verify passwords for encrypted spreadsheets
    for table_name in table_names:
        spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=table_name).first()
        if not spreadsheet:
            return jsonify({"success": False, "message": f"Spreadsheet '{table_name}' not found."})
        if spreadsheet.encrypted:
            if not password:
                return jsonify({"success": False, "message": f"Password required for spreadsheet '{table_name}'."})
            if not verify_password(spreadsheet.password_salt, spreadsheet.password_hash, password):
                return jsonify({"success": False, "message": f"Incorrect password for spreadsheet '{table_name}'."})
            # Store password in session for later use (consider security implications)
            session[table_name] = password
    try:
        # Fetch columns
        columns = get_columns()

        x_axis_options = [col for col in columns if col != "spreadsheet_id"]
        y_axis_options = [col for col in columns if col not in ["spreadsheet_id", "time_start_of_stage", "id"]]

        return jsonify({
            "success": True,
            "x_axis_options": x_axis_options,
            "y_axis_options": y_axis_options
        })
    except Exception as e:
        logger.debug(f"Error loading table: {str(e)}")
        return jsonify({"success": False, "message": f"Error loading table: {str(e)}"})

def decrypt_value(encrypted_value, key, iv):
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(base64.b64decode(encrypted_value)) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted_data.decode('utf-8')

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

            # Get the decryption password once
        decrypt_password = request.form.get('decrypt_password')
        decryption_keys = {}

        # Fetch data using SQLAlchemy
        data_frames = []
        for table_name in table_names:
            spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=table_name).first()
            if not spreadsheet:
                continue
            if spreadsheet.encrypted:
                if not decrypt_password:
                    return jsonify({"error": f"Password required for spreadsheet '{table_name}'."}), 401
                if not verify_password(spreadsheet.password_salt, spreadsheet.password_hash, decrypt_password):
                    return jsonify({"error": f"Incorrect password for spreadsheet '{table_name}'."}), 401
                # Derive the encryption key
                key = derive_key(decrypt_password, spreadsheet.key_salt)
                iv = spreadsheet.iv
                # Fetch rows and decrypt values
                rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()
                data = []
                for row in rows:
                    decrypted_row = {}
                    for col in [x_axis] + y_axis:
                        encrypted_value = getattr(row, col)
                        if encrypted_value:
                            decrypted_value = decrypt_value(encrypted_value, key, iv)
                            # Format the value to 2 decimal places before adding to the row
                            decrypted_row[col] = round(float(decrypted_value), 4)  # Here we format the value
                        else:
                            decrypted_row[col] = None
                    decrypted_row['source'] = table_name
                    data.append(decrypted_row)
                df = pd.DataFrame(data)
                data_frames.append(df)
            else:
                rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()
                if not rows:
                    continue
                # Convert rows to DataFrame and format values during extraction
                df = pd.DataFrame([row.__dict__ for row in rows])
                for col in [x_axis] + y_axis:
                    if col in df.columns:
                        # Convert to float and round to 2 decimal places
                        df[col] = pd.to_numeric(df[col], errors='coerce').round(4)
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
            hovermode='closest',
            xaxis=dict(
                tickformat='.2f'  # Round x-axis labels to 2 decimal places
            ),
            yaxis=dict(
                tickformat='.2f'  # Round y-axis labels to 2 decimal places
            )
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
    spreadsheet_name = request.form.get('spreadsheet_name')
    password = request.form.get('password')

    # Validate required fields
    if not column_name or not column_type or not spreadsheet_name:
        return jsonify({"message": "Column name, type, and spreadsheet name are required.", "success": False})

    # Fetch the spreadsheet
    spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=spreadsheet_name).first()
    if not spreadsheet:
        return jsonify({"message": "Spreadsheet not found.", "success": False})

    # If the spreadsheet is encrypted, verify the password
    if spreadsheet.encrypted:
        if not password:
            return jsonify({"message": "Password is required for encrypted spreadsheets.", "success": False})
        if not verify_password(spreadsheet.password_salt, spreadsheet.password_hash, password):
            return jsonify({"message": "Incorrect password.", "success": False})

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

    try:
        # Fetch the rows associated with the spreadsheet
        rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()

        # Check if the number of data points matches the number of rows
        if len(data_list) != len(rows):
            return jsonify({"message": "Data length does not match number of rows.", "success": False})

        # Add the new data to the 'extra_data' JSON field
        for i, row in enumerate(rows):
            if not row.extra_data:
                row.extra_data = {}
            row.extra_data[column_name] = data_list[i]
            db.session.add(row)

        db.session.commit()
        return jsonify({"message": f"Column '{column_name}' added successfully to spreadsheet '{spreadsheet_name}'.", "success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error adding column: {str(e)}", "success": False})


@main.route('/view-data', methods=['POST'])
def view_data():
    spreadsheet_id = request.form.get('spreadsheet_id')
    password = request.form.get('password')

    spreadsheet = Spreadsheet.query.get(spreadsheet_id)
    if not spreadsheet or not spreadsheet.encrypted:
        return jsonify({'success': False, 'message': 'Spreadsheet not found or not encrypted.'})

    # Retrieve the encrypted data, salt, and IV
    salt = spreadsheet.key_salt
    iv = spreadsheet.iv
    encrypted_row = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet_id).first()
    encrypted_data = encrypted_row.encrypted_data

    # Derive the key from the password
    key = derive_key(password, salt)

    # Attempt to decrypt
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        data_bytes = unpadder.update(padded_data) + unpadder.finalize()
        # Convert bytes back to DataFrame
        df = pd.read_json(data_bytes.decode())
        # Proceed to display or process the DataFrame
        return jsonify({'success': True, 'data': df.to_dict()})
    except Exception as e:
        # Decryption failed
        return jsonify({'success': False, 'message': 'Incorrect password or corrupted data.'})

@main.route('/get-tables', methods=['GET'])
def get_tables_route():
    tables = get_tables()
    return jsonify({'tables': tables})

