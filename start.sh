#!/bin/bash

# =============================================================================
# Script: start.sh
# Description: 
#   - Mounts an SMB/NAS share based on the host OS.
#   - For Windows:
#       - Sets DATABASE_PATH.
#       - Sets up and activates a Python virtual environment.
#       - Installs dependencies.
#       - Runs the Flask application.
#       - Opens the application in the default browser.
#   - For Linux/macOS:
#       - Mounts the SMB/NAS share.
#       - Sets DATABASE_PATH.
#       - Checks Docker daemon.
#       - Uses Docker Compose to build and run containers.
#       - Monitors container health.
#       - Opens the application in the default browser.
# Usage: ./start.sh "[SMB_PATH]"
#        - SMB_PATH: Optional argument to specify a custom SMB share path.
#                  Default is "smb://drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735"
# =============================================================================

# =============================================================================
# Function: cleanup
# Description: Handles cleanup actions when the script is interrupted.
# =============================================================================
cleanup() {
    echo -e "\nStopping processes..."

    # Deactivate virtual environment if active (Windows)
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        deactivate
        echo "Virtual environment deactivated."
    fi

    # Stop Docker containers (Linux/macOS)
    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
        echo "Stopping Docker containers..."
        docker compose down
        echo "Docker containers stopped."
    fi

    echo "Cleanup completed."
    exit 0
}

# Trap Ctrl+C (SIGINT) and call cleanup
trap cleanup SIGINT

# =============================================================================
# Function: check_python
# Description: Checks if Python is installed on Windows.
# =============================================================================
check_python() {
    python_version=$(powershell.exe -Command "python --version" 2>&1)

    if [[ $python_version == *"Python"* ]]; then
        echo "Python is installed. Version: $python_version"
    else
        echo "Python is not installed. Please install Python and try again."
        exit 1
    fi
}

# =============================================================================
# Function: setup_venv
# Description: Sets up a Python virtual environment.
# =============================================================================
setup_venv() {
    # Check if a virtual environment exists in the current directory
    if [[ -f "venv/bin/activate" || -f "venv/Scripts/activate" ]]; then
        echo "A virtual environment exists in this folder."
    else
        echo "No virtual environment found in this folder."
        echo "Creating a virtual environment..."
        python -m venv venv
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create virtual environment."
            exit 1
        fi
    fi
}

# =============================================================================
# Function: activate_venv
# Description: Activates the Python virtual environment.
# =============================================================================
activate_venv() {
    echo "Activating virtual environment..."
    # For Git Bash on Windows, use forward slashes
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "venv/Scripts/activate"
    else
        source "venv/bin/activate"
    fi

    if [ $? -ne 0 ]; then
        echo "Error: Failed to activate virtual environment."
        exit 1
    fi
}

# =============================================================================
# Function: set_env_vars_windows
# Description: Sets environment variables on Windows via PowerShell.
# =============================================================================
set_env_vars_windows() {
    echo "Setting environment variables via PowerShell..."
    powershell.exe -Command "[System.Environment]::SetEnvironmentVariable('FLASK_APP', 'app.py', 'User')"
    powershell.exe -Command "[System.Environment]::SetEnvironmentVariable('FLASK_ENV', 'development', 'User')"
    powershell.exe -Command "[System.Environment]::SetEnvironmentVariable('FLASK_DEBUG', '1', 'User')"
    powershell.exe -Command "[System.Environment]::SetEnvironmentVariable('DATABASE_PATH', 'Z:/soil_tests.db', 'User')"
}

# =============================================================================
# Function: set_env_vars_unix
# Description: Sets environment variables on Unix-like systems.
# =============================================================================
set_env_vars_unix() {
    echo "Setting environment variables..."
    export FLASK_APP=app.py
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export DATABASE_PATH="$DATABASE_PATH"

}

# =============================================================================
# Function: set_env_vars
# Description: Sets environment variables based on OS.
# =============================================================================
set_env_vars() {
    if [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        set_env_vars_windows
    else
        set_env_vars_unix
    fi
}

# =============================================================================
# Function: install_cifs_utils
# Description: Installs cifs-utils on Linux systems if not already installed.
# =============================================================================
install_cifs_utils() {
    if command -v mount.cifs >/dev/null 2>&1; then
        echo "cifs-utils is already installed."
    else
        echo "cifs-utils not found. Installing..."
        # Detect package manager and install cifs-utils
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update
            sudo apt-get install -y cifs-utils
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y cifs-utils
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y cifs-utils
        else
            echo "Unsupported package manager. Please install cifs-utils manually."
            exit 1
        fi
        echo "cifs-utils installed successfully."
    fi
}

# =============================================================================
# Function: mount_linux
# Description: Mounts the SMB share on Linux systems to /mnt/<SMB_SHARENAME>.
# Arguments:
#   $1 - SMB share path (e.g., //server/share)
# =============================================================================
mount_linux() {
    local smb_share="$1"
    
    # Extract the share name from the SMB share path
    share_name=$(echo "$smb_share" | awk -F/ '{print $NF}')
    mount_point="/mnt/$share_name"
    
    # Install cifs-utils if necessary
    install_cifs_utils
    
    # Check if already mounted
    if mountpoint -q "$mount_point"; then
        echo "Mount point $mount_point is already mounted."
    else
        # Ensure the SMB share starts with //
        if [[ "$smb_share" != "//"* ]]; then
            smb_share="//${smb_share}"
        fi
        # Create mount point directory
        echo "Creating mount point at $mount_point..."
        sudo mkdir -p "$mount_point"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create mount point at $mount_point."
            exit 1
        fi
        # Mount the SMB share with provided credentials
        echo "Mounting SMB share $smb_share to $mount_point..."
        sudo mount.cifs "$smb_share" "$mount_point" -o vers=3.0,username="${SMB_USERNAME}",password="${SMB_PASSWORD}",uid=$(id -u),gid=$(id -g),file_mode=0775,dir_mode=0775
        if [ $? -ne 0 ]; then
            echo "Error: Failed to mount SMB share on Linux."
            exit 1
        fi
        echo "Mounted SMB share successfully on Linux."
    fi
    
    # Set NAS_MOUNT_PATH to the actual mount point
    NAS_MOUNT_PATH="$mount_point"
}

# =============================================================================
# Function: mount_macos
# Description: Mounts the SMB share on macOS systems using osascript.
# Arguments:
#   $1 - SMB share path without protocol (e.g., drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735)
# =============================================================================
mount_macos() {
    local smb_share="$1"
    
    # Extract the share name from the smb_share path
    share_name=$(echo "$smb_share" | awk -F/ '{print $NF}')
    mount_point="/Volumes/$share_name"
    
    # Check if already mounted
    if mount | grep "$mount_point" >/dev/null 2>&1; then
        echo "Mount point $mount_point is already mounted."
    else
        # Mount the SMB share via osascript
        echo "Mounting SMB share smb://$smb_share to $mount_point..."
        osascript -e "mount volume \"smb://$smb_share\""

        if [ $? -ne 0 ]; then
            echo "Error: Failed to mount SMB share on macOS."
            exit 1
        fi
        echo "Mounted SMB share successfully on macOS."
    fi
    
    # Set NAS_MOUNT_PATH to the actual mount point
    NAS_MOUNT_PATH="$mount_point"
}

# =============================================================================
# Function: mount_windows
# Description: Mounts the SMB share on Windows systems to a drive letter based on the share name.
# Arguments:
#   $1 - SMB share path (e.g., //server/share)
# =============================================================================
mount_windows() {
    local smb_share="$1"

    # Extract the share name from the SMB share path
    share_name=$(echo "$smb_share" | awk -F/ '{print $NF}')

    # Determine the drive letter based on the share name
    drive_letter="Z:"

    # Check if the drive is already mapped
    if net use "$drive_letter" >/dev/null 2>&1; then
        echo "Drive $drive_letter is already in use. Unmapping..."
        net use "$drive_letter" /delete /y
        if [ $? -ne 0 ]; then
            echo "Error: Failed to unmap drive $drive_letter."
            exit 1
        fi
    fi

    # Convert SMB share path to UNC path (\\server\share)
    unc_path="\\\\$(echo "$smb_share" | sed 's/\//\\/g')"
    echo "UNC Path: $unc_path"

    # Check if SMB_USERNAME and SMB_PASSWORD are set
    if [ -n "$SMB_USERNAME" ] && [ -n "$SMB_PASSWORD" ]; then
        echo "Mapping SMB share with provided credentials..."
        net use "$drive_letter" "$unc_path" /user:"$SMB_USERNAME" "$SMB_PASSWORD" /persistent:no
    else
        echo "Mapping SMB share using existing credentials..."
        net use "$drive_letter" "$unc_path" /persistent:no
    fi

    # Check if the mapping was successful
    if [ $? -ne 0 ]; then
        echo "Error: Failed to map SMB share on Windows."
        exit 1
    fi
    echo "Mapped SMB share successfully on Windows."

    # Set NAS_MOUNT_PATH to the drive letter
    NAS_MOUNT_PATH="${drive_letter}/"
}

# =============================================================================
# Function: parse_smb_path
# Description: Cleans the SMB path by removing the protocol prefix if present.
# Arguments:
#   $1 - Input SMB path (e.g., smb://server/share)
# Output:
#   Cleaned SMB share path (e.g., //server/share)
# =============================================================================
parse_smb_path() {
    local input_path="$1"
    # Remove 'smb://' or 'cifs://' if present
    local cleaned_path="${input_path#smb://}"
    cleaned_path="${cleaned_path#cifs://}"
    echo "$cleaned_path"
}

# =============================================================================
# Function: validate_env_vars
# Description: Validates that necessary environment variables are set for Linux and Windows.
# =============================================================================
validate_env_vars() {
    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if [ -z "$SMB_USERNAME" ] || [ -z "$SMB_PASSWORD" ]; then
            echo "Error: SMB_USERNAME and SMB_PASSWORD must be set in your environment."
            echo "Please add the following lines to your ~/.bashrc or ~/.zshrc:"
            echo "export SMB_USERNAME='your_username'"
            echo "export SMB_PASSWORD='your_password'"
            exit 1
        fi
    fi
}

# =============================================================================
# Function: set_database_path
# Description: Sets the DATABASE_PATH and LOCKFILE_PATH environment variables based on OS.
# =============================================================================
set_database_path() {
    if [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows SMB path using mapped drive
        export DATABASE_PATH="\\\\drive.irds.uwa.edu.au\\RES-ENG-CITS3200-P000735\\soil_tests.db"
        export LOCKFILE_PATH="Z:/lock.lock"  # Set LOCKFILE_PATH for Windows
    else
        # Non-Windows SMB path
        export DATABASE_PATH="$NAS_MOUNT_PATH/soil_tests.db"
        export LOCKFILE_PATH="$NAS_MOUNT_PATH/lock.lock"  
    fi
}
# =============================================================================
# Function: open_browser
# Description: Opens the application in the default browser based on OS.
# =============================================================================
open_browser() {
    case "$OSTYPE" in
      linux*)
        xdg-open http://127.0.0.1:5123  # Linux
        ;;
      darwin*)
        open http://127.0.0.1:5123  # macOS
        ;;
      cygwin* | msys* | win32*)
        # Use PowerShell to open the browser on Windows
        powershell.exe -Command "Start-Process 'http://127.0.0.1:5123/'"
        ;;
      *)
        echo "Warning: OS not recognized. Please manually open the browser at http://127.0.0.1:5123"
        ;;
    esac
}

# =============================================================================
# Function: check_docker_daemon
# Description: Checks if the Docker daemon is running on Linux/macOS.
# =============================================================================
check_docker_daemon() {
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
}

# =============================================================================
# Function: start_docker
# Description: Starts Docker Compose and waits for the container to become healthy.
# =============================================================================
start_docker() {
    echo "Starting Docker containers..."
    docker compose up -d

    echo "Waiting for the Docker container to become healthy..."
    while true; do
        sleep 5
        # Fetch the health status of the container using service name
        service_name="web"  # Ensure this matches your service name in docker-compose.yml
        container_id=$(docker compose ps -q "$service_name")

        if [ -z "$container_id" ]; then
            echo "Error: Service '$service_name' not found in docker-compose.yml."
            exit 1
        fi

        container_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null)

        if [ "$container_status" = "healthy" ]; then
            echo "Docker container is healthy and running."
            break
        elif [ "$container_status" = "unhealthy" ]; then
            echo "Docker container is unhealthy. Check logs for details."
            docker logs "$container_id"
            exit 1
        elif [ "$container_status" = "none" ]; then
            # If no healthcheck is defined, consider it healthy once it's running
            container_state=$(docker inspect --format='{{.State.Running}}' "$container_id" 2>/dev/null)
            if [ "$container_state" = "true" ]; then
                echo "Docker container is running."
                break
            fi
        else
            echo "Still waiting for container to become healthy..."
        fi
    done
}

# =============================================================================
# Main Script Execution Starts Here
# =============================================================================

# =============================================================================
# Validate Environment Variables (only for Linux and Windows)
# =============================================================================
validate_env_vars

# =============================================================================
# Define Default SMB Share Path
# =============================================================================
DEFAULT_SMB_PATH="smb://drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735"

# =============================================================================
# Parse Optional SMB Path Argument
# =============================================================================
if [ -n "$1" ]; then
    SMB_PATH_INPUT="$1"
    echo "Using provided SMB path: $SMB_PATH_INPUT"
else
    SMB_PATH_INPUT="$DEFAULT_SMB_PATH"
    echo "Using default SMB path: $SMB_PATH_INPUT"
fi

# =============================================================================
# Clean SMB Path
# =============================================================================
SMB_SHARE=$(parse_smb_path "$SMB_PATH_INPUT")
echo "Parsed SMB share: $SMB_SHARE"

# =============================================================================
# Detect Operating System and Mount SMB Share Accordingly
# =============================================================================
case "$OSTYPE" in
  linux*)
    echo "Detected Linux OS."
    mount_linux "$SMB_SHARE"
    ;;
  darwin*)
    echo "Detected macOS."
    mount_macos "$SMB_SHARE"
    ;;
  cygwin* | msys* | win32*)
    echo "Detected Windows OS."
    mount_windows "$SMB_SHARE"
    ;;
  *)
    echo "Error: Unsupported OS type: $OSTYPE"
    exit 1
    ;;
esac

echo "NAS_MOUNT_PATH is set to: $NAS_MOUNT_PATH"

# =============================================================================
# Set DATABASE_PATH
# =============================================================================
set_database_path
echo "DATABASE_PATH is set to: $DATABASE_PATH"

wait_for_flask() {
    echo "Waiting for Flask to start..."
    until curl -s http://127.0.0.1:5123 > /dev/null; do
        sleep 2
        echo -n "."
    done
    echo ""
    echo "Flask is up and running."
}

# =============================================================================
# Execute Based on OS
# =============================================================================
if [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # ============================
    # Windows: Use Python Virtual Environment
    # ============================

    # =============================================================================
    # Check if Python is Installed
    # =============================================================================
    check_python

    # =============================================================================
    # Set Up Virtual Environment
    # =============================================================================
    setup_venv

    # =============================================================================
    # Activate Virtual Environment
    # =============================================================================
    activate_venv

    # =============================================================================
    # Run venvcheck.py
    # =============================================================================
    echo "Running venvcheck.py..."
    python venvcheck.py
    if [ $? -ne 0 ]; then
        echo "Error: venvcheck.py failed."
        exit 1
    fi

    # =============================================================================
    # Set Environment Variables
    # =============================================================================
    set_env_vars

    # =============================================================================
    # Echo Environment Variables
    # =============================================================================
    echo "FLASK_APP: $FLASK_APP"
    echo "FLASK_ENV: $FLASK_ENV"
    echo "FLASK_DEBUG: $FLASK_DEBUG"
    echo "DATABASE_PATH: $DATABASE_PATH"

    # =============================================================================
    # Install Python Dependencies
    # =============================================================================
    echo "Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install Python dependencies."
        exit 1
    fi

    # =============================================================================
    # Run Flask Application
    # =============================================================================
    echo "Starting Flask application..."
    flask run --host=0.0.0.0 --port=5123 &
    FLASK_PID=$!

    # =============================================================================
    # Wait for Flask to Start
    # =============================================================================
    echo "Waiting for Flask to initialize..."
    wait_for_flask

    # =============================================================================
    # Open the Application in the Default Browser Based on OS
    # =============================================================================
    open_browser

    # =============================================================================
    # Keep the Script Running to Allow Cleanup on Ctrl+C
    # =============================================================================
    echo "Press Ctrl+C to stop the Flask application and exit."
    wait $FLASK_PID

elif [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
    # ============================
    # Linux/macOS: Use Docker
    # ============================

    # =============================================================================
    # Check if Docker Daemon is Running
    # =============================================================================
    check_docker_daemon

    # =============================================================================
    # Start Docker Compose and Wait for Container to Become Healthy
    # =============================================================================
    start_docker

    # =============================================================================
    # Open the Application in the Default Browser Based on OS
    # =============================================================================
    open_browser

    # =============================================================================
    # Keep the Script Running to Allow Cleanup on Ctrl+C
    # =============================================================================
    echo "Press Ctrl+C to stop the Docker containers and exit."
    while :; do
        sleep 1
    done

else
    echo "Error: Unsupported OS type: $OSTYPE"
    exit 1
fi
