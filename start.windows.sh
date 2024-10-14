#!/bin/bash

export DATABASE_PATH="//drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735/soil_test_results.db"

# Check if Python is installed
python_version=$(powershell -Command "python --version" 2>&1)

if [[ $python_version == *"Python"* ]]; then
    echo "Python is installed. Version: $python_version"
else
    echo "Python is not installed."
fi

# Check if a virtual environment exists in the current directory
if [[ -f "venv/bin/activate" || -f "venv/Scripts/activate" ]]; then
    echo "A virtual environment exists in this folder."
else
    echo "No virtual environment found in this folder."
    echo "Creating a virtual environment"
    python -m venv venv
fi

echo "Activating virtual environment"
source "venv\Scripts\activate"

# Add proper check, right now we are assuming it's working fine
python venvcheck.py

powershell -Command "[System.Environment]::SetEnvironmentVariable('FLASK_APP', 'app.py', 'User')"
powershell -Command "[System.Environment]::SetEnvironmentVariable('FLASK_ENV', 'development', 'User')"
powershell -Command "[System.Environment]::SetEnvironmentVariable('FLASK_DEBUG', '1', 'User')"
# powershell -Command "[System.Environment]::SetEnvironmentVariable('DATABASE_PATH', "\/\/drive.irds.uwa.edu.au\/RES-ENG-CITS3200-P000735", 'User')"



echo "FLASK_APP: $FLASK_APP"
echo "FLASK_ENV: $FLASK_ENV"
echo "FLASK_DEBUG: $FLASK_DEBUG"
echo "DATABASE_PATH: $DATABASE_PATH"

pip install --no-cache-dir -r requirements.txt

flask run --host=0.0.0.0 --port=5123

sleep 60

Start-Process "http://127.0.0.1:5123/"