# app/blueprints/main.py
from flask import Blueprint, render_template, request
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import io
import base64

main = Blueprint('main', __name__)

# Example database connection setup
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
    x_axis_options = [col for col in columns if "Time" in col or "Sec" in col or "hours" in col]

    # Define potential Y-axis options (e.g., pressure, volume, strain)
    y_axis_options = [col for col in columns if col not in x_axis_options]

    return render_template('home.html', columns=columns, x_axis_options=x_axis_options, y_axis_options=y_axis_options)

@main.route('/plot', methods=['POST'])
def plot():
    selected_columns = request.form.getlist('columns')
    x_axis = request.form['x_axis']
    y_axis = request.form['y_axis']

    # Query the selected columns from the database
    conn = sqlite3.connect(DATABASE_PATH)
    query = f"SELECT {', '.join(selected_columns)} FROM CSL_1_U"  # Adjust your table name
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Generate plot
    plt.figure(figsize=(10, 6))
    plt.plot(df[x_axis], df[y_axis], marker='o')
    plt.xlabel(x_axis)
    plt.ylabel(y_axis)
    plt.title('User-Generated Plot')

    # Save plot to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Convert to base64 to display directly in the HTML
    plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
    plot_url = f"data:image/png;base64,{plot_url}"

    return render_template('home.html', plot_url=plot_url, columns=selected_columns)

