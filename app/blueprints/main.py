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

    if 'excel_files' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request.'})

    files = request.files.getlist('excel_files')
    
    if not files:
        return jsonify({'success': False, 'message': 'No file selected.'})

    for file in files:
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            sheet_name = '03 - Shearing'  # Adjust as necessary
            df = data_extractor(file, sheet_name)
            name = filename.rsplit('.', 1)[0]

            if encrypt_data:
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

                result = insert_data_to_db(
                    name, df, spreadsheet=spreadsheet, encrypt=True, encryption_key=key, iv=iv
                )
            else:
                result = insert_data_to_db(name, df)
            
            if not result['success']:
                return jsonify({'success': False, 'message': result['message']})

             # Reset file pointer to read again for instance extraction
            file.seek(0)
            instances = find_instances(file)
            if instances:
                insert_instances_to_db(name, instances)

    return jsonify({'success': True, 'message': 'Files uploaded and processed successfully.'})

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
        x_axis = request.form.get('x_axis')
        y_axis = request.form.getlist('y_axis')
        filtered_spreadsheet_ids = request.form.get('filtered_spreadsheet_ids')
        decrypt_password = request.form.get('decrypt_password')

        if not x_axis:
            return jsonify({"error": "X-axis field is missing from the request."}), 400

        if not y_axis:
            return jsonify({"error": "Please select at least one column for the Y-axis."}), 400

        if not filtered_spreadsheet_ids:
            return jsonify({"error": "No spreadsheets selected for plotting."}), 400

        spreadsheet_ids = json.loads(filtered_spreadsheet_ids)

        # Fetch data using SQLAlchemy
        data_frames = []
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']  # Extended colors
        color_map = {}

        for idx, spreadsheet_id in enumerate(spreadsheet_ids):
            spreadsheet = Spreadsheet.query.get(spreadsheet_id)
            if not spreadsheet:
                logger.debug(f"Spreadsheet ID {spreadsheet_id} not found.")
                continue
            table_name = spreadsheet.spreadsheet_name
            color_map[table_name] = colors[idx % len(colors)]  # Map table name to a color

            if spreadsheet.encrypted:
                if not decrypt_password:
                    return jsonify({"error": f"Password required for spreadsheet '{table_name}'."}), 401
                if not verify_password(spreadsheet.password_salt, spreadsheet.password_hash, decrypt_password):
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
                # Drop rows with NaN in x_axis
                df.dropna(subset=[x_axis], inplace=True)
                data_frames.append(df)
            else:
                rows = SpreadsheetRow.query.filter_by(spreadsheet_id=spreadsheet.spreadsheet_id).all()
                if not rows:
                    logger.debug(f"No rows found for spreadsheet '{table_name}'.")
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
                # Drop rows with NaN in x_axis
                df.dropna(subset=[x_axis], inplace=True)
                data_frames.append(df)

        if not data_frames:
            return jsonify({"error": "No data found for the selected spreadsheets."}), 404

        data = pd.concat(data_frames, ignore_index=True)

        # Create a Plotly figure
        fig = go.Figure()

        for y in y_axis:
            for table_name in data['source'].unique():
                table_data = data[data['source'] == table_name]
                fig.add_trace(go.Scatter(
                    x=table_data[x_axis],
                    y=table_data[y],
                    mode='markers+lines',
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

        # Customize the layout with legend
        fig.update_layout(
            title='Interactive Plot',
            xaxis_title=x_axis.replace('_', ' ').capitalize(),
            yaxis_title=', '.join([col.replace('_', ' ').capitalize() for col in y_axis]),
            legend_title="Source Tables",
            hovermode='closest',
            xaxis=dict(
                tickformat='.2f'
            ),
            yaxis=dict(
                tickformat='.2f'
            ),
            margin=dict(l=50, r=50, t=50, b=50),
            dragmode='pan',  # Enables dragging
            legend=dict(
                x=0.95,
                y=0.95,
                xanchor='right',
                yanchor='top',
                traceorder="normal",
                bgcolor="rgba(255, 255, 255, 0.5)",  # Transparent background for the legend
                bordercolor="Black",
                borderwidth=1
            )
        )

        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return jsonify({"graph_json": graph_json})

    except Exception as e:
        logger.exception(f"Error during plotting: {str(e)}")
        return jsonify({"error": f"Error during plotting: {str(e)}"}), 500

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

@main.route('/load-instances', methods=['POST'])
def load_instances():
    try:
        # Retrieve instances from the form data
        instances_json = request.form.get('instances')
        if not instances_json:
            return jsonify({"success": False, "message": "No instances provided."})

        instances = json.loads(instances_json)

        # Find spreadsheets that match the selected instances and values
        matching_spreadsheet_ids = set()
        for instance in instances:
            name = instance['name']
            values = instance['values']
            # Find instance IDs that match the name and selected values
            instance_ids = Instance.query.filter(
                Instance.instance_name == name,
                Instance.instance_value.in_(values)
            ).with_entities(Instance.instance_id).all()
            if not instance_ids:
                continue
            instance_ids = [i[0] for i in instance_ids]
            # Find spreadsheets associated with these instances
            spreadsheet_ids = SpreadsheetInstance.query.filter(
                SpreadsheetInstance.instance_id.in_(instance_ids)
            ).with_entities(SpreadsheetInstance.spreadsheet_id).all()
            spreadsheet_ids = [si[0] for si in spreadsheet_ids]
            if not matching_spreadsheet_ids:
                matching_spreadsheet_ids.update(spreadsheet_ids)
            else:
                # Intersection to ensure spreadsheets match all selected instances
                matching_spreadsheet_ids.intersection_update(spreadsheet_ids)

        if not matching_spreadsheet_ids:
            return jsonify({"success": False, "message": "No spreadsheets match the selected instances."})

        # Retrieve column options
        columns = get_columns()
        x_axis_options = [col for col in columns if col != "spreadsheet_id"]
        y_axis_options = [col for col in columns if col not in ["spreadsheet_id", "time_start_of_stage", "id"]]

        return jsonify({
            "success": True,
            "x_axis_options": x_axis_options,
            "y_axis_options": y_axis_options,
            "filtered_spreadsheet_ids": list(matching_spreadsheet_ids)
        })

    except Exception as e:
        logger.debug(f"Error loading instances: {str(e)}")
        return jsonify({"success": False, "message": f"Error loading instances: {str(e)}"})


@main.route('/load-filters', methods=['POST'])
def load_filters():
    try:
        # Get filter type
        filter_type = request.form.get('filter_type', 'both')

        # Get selected tables
        selected_tables = request.form.getlist('table_name[]')
        selected_spreadsheet_query = Spreadsheet.query

        if selected_tables:
            # Filter spreadsheets by selected table names
            selected_spreadsheet_query = selected_spreadsheet_query.filter(
                Spreadsheet.spreadsheet_name.in_(selected_tables)
            )

        # Get instances from the form data
        instances_json = request.form.get('instances', '[]')  # Default to empty list if not provided

        logger.debug(f"Selected Tables: {selected_tables}")
        logger.debug(f"Instances JSON: {instances_json}")
        logger.debug(f"Filter Type: {filter_type}")

        try:
            instances = json.loads(instances_json)
        except json.JSONDecodeError:
            instances = []

        if instances:
            # Apply instance filters
            for instance in instances:
                name = instance['name']
                values = instance['values']
                selected_spreadsheet_query = selected_spreadsheet_query.filter(
                    Spreadsheet.instances.any(
                        and_(
                            Instance.instance_name == name,
                            Instance.instance_value.in_(values)
                        )
                    )
                )

        # Execute the query to get the final list of spreadsheet IDs
        final_spreadsheet_ids = [s.spreadsheet_id for s in selected_spreadsheet_query.all()]

        if not final_spreadsheet_ids:
            return jsonify({"success": False, "message": "No spreadsheets match the selected filters."})

        # Retrieve column options
        columns = get_columns()
        x_axis_options = [col for col in columns if col != "spreadsheet_id"]
        y_axis_options = [col for col in columns if col not in ["spreadsheet_id", "time_start_of_stage", "id"]]

        return jsonify({
            "success": True,
            "x_axis_options": x_axis_options,
            "y_axis_options": y_axis_options,
            "filtered_spreadsheet_ids": list(final_spreadsheet_ids)
        })

    except Exception as e:
        logger.exception(f"Error loading filters: {str(e)}")
        return jsonify({"success": False, "message": f"Error loading filters: {str(e)}"})

