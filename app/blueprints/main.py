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
    Instance,
    SpreadsheetInstance,
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
import time
from werkzeug.utils import secure_filename
import hashlib

import numpy as np
from sqlalchemy import and_, or_


LOCKFILE_PATH = '/mnt/irds/lockfile.lock'  # Path to the lock file on the NAS

def acquire_lock(timeout=30, max_lock_age=300, check_interval=1):
    """Attempt to acquire a lock by creating a lockfile.
       If the lockfile is older than max_lock_age seconds, override it."""
    start_time = time.time()
    while True:
        try:
            # Attempt to create the lock file exclusively
            fd = os.open(LOCKFILE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            # Write the current timestamp to the lock file
            with os.fdopen(fd, 'w') as f:
                f.write(str(time.time()))
            # Lock acquired
            return True
        except FileExistsError:
            # Lock file exists, check its age
            lock_age = time.time() - os.path.getmtime(LOCKFILE_PATH)
            if lock_age > max_lock_age:
                # Assume the lock is stale and override it
                print("Stale lock detected. Overriding the lock.")
                try:
                    os.remove(LOCKFILE_PATH)
                except FileNotFoundError:
                    continue  # Another process might have removed it
            else:
                # Check if timeout has been reached
                if time.time() - start_time > timeout:
                    return False
                time.sleep(check_interval)

def release_lock():
    """Release the lock by deleting the lockfile."""
    try:
        os.remove(LOCKFILE_PATH)
    except FileNotFoundError:
        pass  # Lock file already removed


# Set up basic logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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


# app/blueprints/main.py

@main.route('/upload', methods=['POST'])
def upload_file():
    logger.info("Received upload request.")
    
    # Attempt to acquire the lock before writing
    if not acquire_lock():
        logger.warning("Lock acquisition failed. Another upload is in progress.")
        return jsonify({
            'success': False,
            'message': 'Database is currently being updated by another user. Please try again later.'
        }), 423

    logger.debug("Lock acquired successfully.")

    try:
        password = request.form.get('encrypt_password')
        encrypt_data = bool(password)
        logger.debug(f"Encryption password provided: {'Yes' if encrypt_data else 'No'}")

        if 'excel_files' not in request.files:
            logger.error("No 'excel_files' part in the request.")
            return jsonify({'success': False, 'message': 'No file part in the request.'})

        files = request.files.getlist('excel_files')
        logger.debug(f"Number of files received: {len(files)}")

        if not files:
            logger.error("No files selected for upload.")
            return jsonify({'success': False, 'message': 'No file selected.'})

        success_files = []
        failed_files = []

        # Begin a transaction for each file individually
        for idx, file in enumerate(files, start=1):
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                logger.info(f"Processing file {idx}/{len(files)}: {filename}")

                sheet_name = '03 - Shearing'  # Adjust as necessary
                df = data_extractor(file, sheet_name)

                if df.empty:
                    logger.warning(f"No valid data extracted from file: {filename}")
                    failed_files.append({'filename': filename, 'reason': 'No valid data extracted.'})
                    continue  # Skip to the next file

                name = filename.rsplit('.', 1)[0]
                logger.debug(f"Spreadsheet name derived: {name}")

                if encrypt_data:
                    logger.debug("Encryption enabled for this file.")
                    # Encryption logic here
                    salt = os.urandom(16)
                    iv = os.urandom(16)
                    key = derive_key(password, salt)
                    password_salt, password_hash = hash_password(password)

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
                    logger.debug(f"Added Spreadsheet object for {name} to the session.")

                    result = insert_data_to_db(
                        name, df, spreadsheet=spreadsheet, encrypt=True, encryption_key=key, iv=iv
                    )
                else:
                    logger.debug("Encryption not enabled for this file.")
                    result = insert_data_to_db(name, df)

                if not result['success']:
                    logger.error(f"Failed to insert data for file: {filename}. Reason: {result['message']}")
                    failed_files.append({'filename': filename, 'reason': result['message']})
                    db.session.rollback()  # Rollback current file's transaction
                else:
                    logger.info(f"Successfully inserted data for file: {filename}")
                    success_files.append(filename)

                # Reset file pointer to read again for instance extraction
                file.seek(0)
                instances = find_instances(file)
                logger.debug(f"Found {len(instances)} instances in file: {filename}")

                if instances:
                    try:
                        insert_instances_to_db(name, instances)
                        logger.info(f"Inserted instances for file: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to insert instances for file: {filename}. Reason: {str(e)}")
                        failed_files.append({'filename': filename, 'reason': 'Failed to insert instances.'})
                        db.session.rollback()  # Rollback current file's transaction

                db.session.commit()  # Commit after each file

        if success_files and not failed_files:
            message = f"All files uploaded and processed successfully: {', '.join(success_files)}."
            logger.info(message)
            return jsonify({'success': True, 'message': message})
        elif success_files and failed_files:
            success_message = f"Successfully processed files: {', '.join(success_files)}."
            failure_message = "; ".join([f"{f['filename']} failed: {f['reason']}" for f in failed_files])
            combined_message = f"{success_message} {failure_message}"
            logger.warning(combined_message)
            return jsonify({'success': True, 'message': combined_message})
        else:
            failure_message = "; ".join([f"{f['filename']} failed: {f['reason']}" for f in failed_files])
            logger.error(failure_message)
            return jsonify({'success': False, 'message': failure_message}), 500

    except Exception as e:
        logger.exception(f"Error during upload: {e}")
        # Rollback in case of unexpected errors
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An unexpected error occurred.'}), 500

    finally:
        # Ensure the lock is released even if an error occurs
        release_lock()
        logger.debug("Lock released after upload attempt.")

@main.route('/')
def home():
    try:
        # Get all available tables from the database
        tables = get_tables()
        instances = get_instances()
        columns = get_columns()

        x_axis_options = [col for col in columns if col != "spreadsheet_id"]
        y_axis_options = [col for col in columns if col not in ["spreadsheet_id", "time_start_of_stage", "id"]]
    except Exception as e:
        flash('Unable to connect to the database. Please ensure the NAS is mounted.', 'error')
        tables = []
        instances = {}
        x_axis_options = []
        y_axis_options = []
    return render_template('home.html', tables=tables, instances=instances, x_axis_options=x_axis_options, y_axis_options=y_axis_options)


def decrypt_value(encrypted_value, key, iv):
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(base64.b64decode(encrypted_value)) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted_data.decode('utf-8')

@main.route('/plot', methods=['POST'])
def plot():
    if not acquire_lock():
        logger.warning("Plot request denied due to active lock.")
        return jsonify({
            'success': False,
            'message': 'Another operation is in progress. Please try again later.'
        }), 423

    logger.info("Lock acquired for plotting.")
    try:
        # Retrieve form data
        x_axis = request.form.get('x_axis')
        y_axis = request.form.getlist('y_axis')
        selected_tables = request.form.getlist('table_name[]')
        instances_json = request.form.get('instances_json')
        
        # Collect decryption passwords from the form
        decrypt_passwords = {}
        for table_name in selected_tables:
            password_field = f"password_{table_name}"
            decrypt_passwords[table_name] = request.form.get(password_field)

        preset = request.form.get('preset-options')

        if preset == "None":
            # Input validation
            if not x_axis:
                logger.error("Missing X-axis in plot request.")
                return jsonify({"error": "X-axis field is missing from the request."}), 400

            if not y_axis:
                logger.error("No Y-axis selected in plot request.")
                return jsonify({"error": "Please select at least one column for the Y-axis."}), 400
              
            if not filtered_spreadsheet_ids:
                return jsonify({"error": "No spreadsheets selected for plotting."}), 400

        logger.debug(f"Plot parameters - X-axis: {x_axis}, Y-axis: {y_axis}, Tables: {selected_tables}, Instances: {instances_json}")


        # Process selected tables and instances to get spreadsheet IDs
        spreadsheet_ids = set()

        if selected_tables:
            # Get spreadsheet IDs from selected tables
            spreadsheets = Spreadsheet.query.filter(Spreadsheet.spreadsheet_name.in_(selected_tables)).all()
            spreadsheet_ids.update([s.spreadsheet_id for s in spreadsheets])
            logger.debug(f"Found {len(spreadsheet_ids)} spreadsheet IDs from selected tables.")


        if instances_json:
            instances = json.loads(instances_json)
            for instance in instances:
                name = instance['name']
                values = instance['values']
                # Find instance IDs that match the name and selected values
                instance_ids = Instance.query.filter(
                    Instance.instance_name == name,
                    Instance.instance_value.in_(values)
                ).with_entities(Instance.instance_id).all()
                if not instance_ids:
                    logger.warning(f"No instances found for {name} with values {values}.")
                    continue
                instance_ids = [i[0] for i in instance_ids]
                # Find spreadsheets associated with these instances
                spreadsheet_ids_query = SpreadsheetInstance.query.filter(
                    SpreadsheetInstance.instance_id.in_(instance_ids)
                ).with_entities(SpreadsheetInstance.spreadsheet_id)
                spreadsheet_ids.update([s[0] for s in spreadsheet_ids_query.all()])
            logger.debug(f"Total unique spreadsheet IDs after processing instances: {len(spreadsheet_ids)}")


        if not spreadsheet_ids:
            logger.error("No spreadsheets match the selected filters.")
            return jsonify({"error": "No spreadsheets match the selected filters."}), 400

        # Fetch data using SQLAlchemy
        data_frames = []
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']  # Extended colors
        color_map = {}

        selected_y_columns = y_axis # This variable is for containing manually selected y_axis which will be 
                                    #used if calculated preset options are selected 

        # Non-calculated preset options
        # Columns in preset options get added to y_axis
        if preset == "non_calc_1":
            y_axis = ['p', 'q', 'induced_PWP'] + y_axis
            x_axis = 'axial_strain'
        if preset == "non_calc_2":
            y_axis = ['q'] + y_axis
            x_axis = 'p'
        if preset == "non_calc_3":
            y_axis = ['vol_strain'] + y_axis
            x_axis = 'axial_strain'
        
        # Calculated preset options
        if preset == "calc_1":
            y_axis = ['e'] + y_axis
            x_axis = 'p'
        if preset == "calc_2":
            y_axis = ['q','p'] + y_axis
            x_axis = 'axial_strain'
        if preset == "calc_3":
            y_axis = ['q', 'p'] + y_axis
            x_axis = 'p'
        
        for idx, spreadsheet_id in enumerate(spreadsheet_ids):
            spreadsheet = Spreadsheet.query.get(spreadsheet_id)
            if not spreadsheet:
                logger.debug(f"Spreadsheet ID {spreadsheet_id} not found.")
                continue
            table_name = spreadsheet.spreadsheet_name
            color_map[table_name] = colors[idx % len(colors)]
            logger.debug(f"Processing Spreadsheet '{table_name}' with color '{color_map[table_name]}'.")

            if spreadsheet.encrypted:
                logger.debug(f"Spreadsheet '{table_name}' is encrypted. Attempting decryption.")
                
                # Retrieve the corresponding password for this encrypted spreadsheet
                decrypt_password = decrypt_passwords.get(table_name)
                if not decrypt_password:
                    logger.error(f"Decryption password not provided for encrypted Spreadsheet '{table_name}'.")
                    return jsonify({"error": f"Password required for spreadsheet '{table_name}'."}), 401
                if not verify_password(spreadsheet.password_salt, spreadsheet.password_hash, decrypt_password):
                    logger.error(f"Incorrect decryption password for Spreadsheet '{table_name}'.")
                    return jsonify({"error": f"Incorrect password for spreadsheet '{table_name}'."}), 401
                key = derive_key(decrypt_password, spreadsheet.key_salt)
                iv = spreadsheet.iv
                rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()
                data = []
                for row in rows:
                    decrypted_row = {}
                    for col in [x_axis] + y_axis:
                        encrypted_value = getattr(row, col)
                        if encrypted_value:
                            decrypted_value = decrypt_value(encrypted_value, key, iv)
                            try:
                                decrypted_row[col] = round(float(decrypted_value), 4)
                            except ValueError:
                                decrypted_row[col] = None
                        else:
                            decrypted_row[col] = None
                    decrypted_row['source'] = table_name
                    data.append(decrypted_row)
                df = pd.DataFrame(data)
                df = df.dropna(subset=[x_axis])
                data_frames.append(df)
                logger.debug(f"Decrypted and cleaned data for Spreadsheet '{table_name}': {len(df)} rows.")

            else:
                rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()
                if not rows:
                    logger.debug(f"No rows found for Spreadsheet '{table_name}'.")
                    continue
                data_dicts = []
                for row in rows:
                    row_dict = {col: getattr(row, col) for col in [x_axis] + y_axis}
                    row_dict['source'] = table_name
                    data_dicts.append(row_dict)
                df = pd.DataFrame(data_dicts)
                for col in [x_axis] + y_axis:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').round(4)
                    else:
                        logger.warning(f"Column '{col}' not found in Spreadsheet '{table_name}'.")
                        df[col] = None
                df = df.dropna(subset=[x_axis])
                logger.debug(f"Cleaned data for Spreadsheet '{table_name}': {len(df)} rows.")
                data_frames.append(df)

        if not data_frames:
            logger.error("No data found for the selected spreadsheets.")
            return jsonify({"error": "No data found for the selected spreadsheets."}), 404

        data = pd.concat(data_frames, ignore_index=True)
        logger.info(f"Combined data contains {len(data)} rows.")

        # Create a Plotly figure
        fig = go.Figure()

        if preset == "calc_1" or preset =="calc_2" or preset == "calc_3":
            for table_name in data['source'].unique():
                table_data = data[data['source'] == table_name]
                if preset == "calc_1": 
                    y_preset = 'e' #Swap x-axis and y-axis (just for this option)
                    x_axis = "log(p')"
                    table_data[x_axis] = np.log(table_data['p'])
                if preset == "calc_2":
                    y_preset = "q/p'"
                    table_data[y_preset] = table_data['q']/table_data['p']
                if preset == "calc_3":
                    qmax = table_data['q'].max()
                    y_preset = "qmax/p'"
                    table_data[y_preset] = qmax/ table_data['p']   
                fig.add_trace(go.Scatter(
                    x=table_data[x_axis],
                    y=table_data[y_preset],
                    mode='markers',
                    name=f"{table_name} - {y_preset}",
                    marker=dict(color=color_map[table_name]),
                    text=table_data['source'],
                    hovertemplate=(
                        f"<b>{y_preset}</b>: %{{y}}<br>"
                        f"<b>{x_axis}</b>: %{{x}}<br>"
                        f"<b>Spreadsheet</b>: %{{text}}<br>"
                        "<extra></extra>"
                        )
                    ))
                for y in selected_y_columns:
                    fig.add_trace(go.Scatter(
                    x=table_data[x_axis],
                    y=table_data[y],
                    mode='markers',
                    name=f"{table_name} - {y}",
                    marker=dict(color=color_map[table_name]),
                    text=table_data['source'],
                    hovertemplate=(
                        f"<b>{y}</b>: %{{y}}<br>"
                        f"<b>{x_axis}</b>: %{{x}}<br>"
                        f"<b>Spreadsheet</b>: %{{text}}<br>"
                        "<extra></extra>"
                        )
                    ))   
            y_axis = [y_preset] + selected_y_columns # Combining calculated column name and selected columns names
            logger.debug(f"Added plot trace for '{table_name} - {y}'.")        
        else:    
            for y in y_axis:
                for table_name in data['source'].unique():
                    table_data = data[data['source'] == table_name]
                    fig.add_trace(go.Scatter(
                        x=table_data[x_axis],
                        y=table_data[y],
                        mode='markers',
                        name=f"{table_name} - {y}",
                        marker=dict(color=color_map[table_name]),
                        text=table_data['source'],
                        hovertemplate=(
                            f"<b>{y}</b>: %{{y}}<br>"
                            f"<b>{x_axis}</b>: %{{x}}<br>"
                            f"<b>Spreadsheet</b>: %{{text}}<br>"
                            "<extra></extra>"
                        )
                    ))
        
        y_axis = ["p'" if y == 'p' else y for y in y_axis] #Add apostrophe to p
        if x_axis == 'p':
            x_axis = "p'"

        x_axis_name = x_axis.replace('_', ' ').capitalize()
        y_axis_name = ', '.join([col.replace('_', ' ').capitalize() for col in y_axis])
        title_name = f"{y_axis_name} vs {x_axis_name}"

        # Customize the layout with legend
        fig.update_layout(
            title=title_name,
            xaxis_title= x_axis_name,
            yaxis_title= y_axis_name,
            legend_title="Source Tables",
            hovermode='closest',
            xaxis=dict(
                tickformat='.2f'
            ),
            yaxis=dict(
                tickformat='.2f'
            ),
            margin=dict(l=50, r=50, t=50, b=50),
            dragmode='pan',
            legend=dict(
                x=0.95,
                y=0.95,
                xanchor='right',
                yanchor='top',
                traceorder="normal",
                bgcolor="rgba(255, 255, 255, 0.5)",
                bordercolor="Black",
                borderwidth=1
            )
        )
        logger.info("Plotly figure created successfully.")

        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        logger.debug("Serialized Plotly figure to JSON.")

        return jsonify({"graph_json": graph_json})

    except Exception as e:
        logger.exception(f"Error during plotting: {e}")
        return jsonify({"error": f"Error during plotting: {e}"}), 500

    finally:
        release_lock()
        logger.info("Lock released after plotting attempt.")

@main.route('/add-data', methods=['GET', 'POST'])
def add_data():
    if request.method == 'POST':
        # Get CSV data from form input or file
        csv_data = request.form.get('csv_data')
        csv_file = request.files.get('csv_file')

        if not csv_data and not csv_file:
            return jsonify({'success': False, 'message': 'No data provided.'})

        # Read the CSV data into a DataFrame
        if csv_file and csv_file.filename != '':
            csv_file.seek(0)
            df = pd.read_csv(csv_file)
        elif csv_data:
            from io import StringIO
            df = pd.read_csv(StringIO(csv_data))
        else:
            return jsonify({'success': False, 'message': 'No data provided.'})

        # Create or get the 'custom_input' spreadsheet
        spreadsheet_name = 'custom_input'
        spreadsheet = Spreadsheet.query.filter_by(spreadsheet_name=spreadsheet_name).first()
        if not spreadsheet:
            spreadsheet = Spreadsheet(spreadsheet_name=spreadsheet_name, encrypted=False)
            db.session.add(spreadsheet)
            db.session.commit()

        # Insert data into the database
        standard_columns = ['time_start_of_stage', 'shear_induced_PWP', 'axial_strain',
                            'vol_strain', 'induced_PWP', 'p', 'q', 'e']

        rows = []
        for _, row in df.iterrows():
            data = {}
            extra_data = {}
            for column in df.columns:
                value = str(row[column]) if pd.notnull(row[column]) else ''
                if column in standard_columns:
                    data[column] = value
                else:
                    extra_data[column] = value
            row_entry = SpreadsheetRow(
                spreadsheet_id=spreadsheet.spreadsheet_id,
                **data,
                extra_data=extra_data
            )
            rows.append(row_entry)
        db.session.bulk_save_objects(rows)
        db.session.commit()
        flash('Data added successfully.', 'success')
        return redirect(url_for('main.home'))
    else:
        return render_template('add_data.html')


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

@main.route('/get-instances', methods=['GET'])
def get_instances_route():
    instances = get_instances()
    return jsonify({'instances': instances})

