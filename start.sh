#!/bin/bash

# =============================================================================
# Script: start.sh
# Description: Mounts an SMB/NAS share based on the host OS, sets the NAS_MOUNT_PATH,
#              and starts the Docker container while handling cleanup on exit.
# Usage: ./start.sh [SMB_PATH]
#        - SMB_PATH: Optional argument to specify a custom SMB share path.
#                  Default is "smb://drive.irds.uwa.edu.au/RES-ENG-CITS3200-P000735"
# =============================================================================

# =============================================================================
# Function: cleanup
# Description: Handles cleanup actions when the script is interrupted.
# =============================================================================
cleanup() {
    echo -e "\nStopping Docker container..."
    docker-compose down
    echo "Docker container stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT) and call cleanup
trap cleanup SIGINT

# =============================================================================
# Function: check_docker_daemon
# Description: Checks if the Docker daemon is running.
# =============================================================================
check_docker_daemon() {
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker daemon is not running. Please start Docker Desktop and try again."
        exit 1
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
        # Mount the SMB share as guest
        echo "Mounting SMB share $smb_share to $mount_point..."
        sudo mount.cifs "$smb_share" "$mount_point" -o vers=3.0,guest,uid=$(id -u),gid=$(id -g),file_mode=0775,dir_mode=0775
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
# Description: Mounts the SMB share on macOS systems using osascript without credentials.
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
# Function: get_drive_letter
# Description: Determines an available drive letter based on the share name.
# Arguments:
#   $1 - Share name
# Output:
#   Selected drive letter or exits if none are available.
# =============================================================================
get_drive_letter() {
    local share_name="$1"
    local desired_letter="${share_name:0:1}"  # First character of share name
    desired_letter=$(echo "$desired_letter" | tr '[:lower:]' '[:upper:]')  # Uppercase
    
    # Ensure it's a letter A-Z
    if [[ ! "$desired_letter" =~ ^[A-Z]$ ]]; then
        desired_letter="Z"  # Default to Z if not a valid letter
    fi
    
    # Check if the desired drive letter is available using PowerShell
    available_letter=$(powershell -Command "
        if (-not (Get-PSDrive -Name '$desired_letter' -ErrorAction SilentlyContinue)) {
            '$desired_letter:'
        } else {
            $available = [char]('Z'..'A' | Where-Object { -not (Get-PSDrive -Name $_ -ErrorAction SilentlyContinue) } | Select-Object -First 1)
            if ($available) { '$available:' } else { 'NONE' }
        }
    ")
    
    if [ "$available_letter" = "NONE" ]; then
        echo "Error: No available drive letters to map the SMB share on Windows."
        exit 1
    fi
    
    echo "$available_letter"
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
    drive_letter=$(get_drive_letter "$share_name")

    # Check if the drive is already mapped
    if net use "$drive_letter" >/dev/null 2>&1; then
        echo "Drive $drive_letter is already in use. Unmapping..."
        net use "$drive_letter" /delete /y
    fi

    # Convert SMB share path to UNC path (\\server\share)
    unc_path="\\\\$(echo "$smb_share" | sed 's/\//\\/g')"

    # Check if SMB_USERNAME and SMB_PASSWORD are set
    if [ -n "$SMB_USERNAME" ] && [ -n "$SMB_PASSWORD" ]; then
        echo "Mapping SMB share with provided credentials..."
        # Use PowerShell to create PSCredential
        powershell -Command "
            \$securePassword = ConvertTo-SecureString '$SMB_PASSWORD' -AsPlainText -Force;
            \$credential = New-Object System.Management.Automation.PSCredential('$SMB_USERNAME', \$securePassword);
            New-SmbMapping -LocalPath '$drive_letter' -RemotePath '$unc_path' -Credential \$credential -Persist \$false
        "
    else
        echo "Mapping SMB share using existing credentials..."
        powershell -Command "New-SmbMapping -LocalPath '$drive_letter' -RemotePath '$unc_path' -Persist \$false"
    fi

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
# Main Script Execution Starts Here
# =============================================================================

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
# Export NAS_MOUNT_PATH for Docker Compose
# =============================================================================
export NAS_MOUNT_PATH

# =============================================================================
# Check if Docker Daemon is Running
# =============================================================================
check_docker_daemon

# =============================================================================
# Check if NAS_MOUNT_PATH Exists (Only for Linux and macOS)
# =============================================================================
if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
    if [ ! -d "$NAS_MOUNT_PATH" ]; then
        echo "Error: NAS_MOUNT_PATH directory does not exist: $NAS_MOUNT_PATH"
        exit 1
    fi
fi

# =============================================================================
# Start Docker Compose and Wait for Container to Become Healthy
# =============================================================================
echo "Starting Docker container..."
docker-compose up -d 

echo "Waiting for the Docker container to become healthy..."
while true; do
    sleep 5
    # Fetch the health status of the container using service name instead of container name
    service_name="web"  # Adjust this to match your docker-compose service name
    container_id=$(docker-compose ps -q "$service_name")
    
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

# =============================================================================
# Open the Application in the Default Browser Based on OS
# =============================================================================
case "$OSTYPE" in
  linux*)
    xdg-open http://127.0.0.1:5123  # Linux
    ;;
  darwin*)
    open http://127.0.0.1:5123  # macOS
    ;;
  cygwin* | msys* | win32*)
    # Use 'start' via cmd.exe for Windows
    cmd.exe /c start "" "http://127.0.0.1:5123"
    ;;
  *)
    echo "Warning: OS not recognized. Please manually open the browser at http://127.0.0.1:5123"
    ;;
esac

# =============================================================================
# Keep the Script Running to Allow Cleanup on Ctrl+C
# =============================================================================
echo "Press Ctrl+C to stop the Docker container and exit."
while :; do
    sleep 1
done

