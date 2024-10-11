#!/bin/bash

# =============================================================================
# Script: start.sh
# Description: Installs necessary utilities, mounts an SMB/NAS share based on
#              the host OS, sets the NAS_MOUNT_PATH, and starts the Docker
#              container while handling cleanup on exit.
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
# Description: Mounts the SMB share on Linux systems.
# Arguments:
#   $1 - SMB share path (e.g., //server/share)
#   $2 - Mount point directory (e.g., /mnt/irds)
# =============================================================================
mount_linux() {
    local smb_share="$1"
    local mount_point="$2"
    
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
        # Mount the SMB share as guest
        echo "Mounting SMB share $smb_share to $mount_point..."
        sudo mount.cifs "$smb_share" "$mount_point" -o vers=3.0,guest,uid=$(id -u),gid=$(id -g),file_mode=0775,dir_mode=0775
        if [ $? -ne 0 ]; then
            echo "Error: Failed to mount SMB share on Linux."
            exit 1
        fi
        echo "Mounted SMB share successfully on Linux."
    fi
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
# Function: mount_windows
# Description: Mounts the SMB share on Windows systems.
# Arguments:
#   $1 - SMB share path (e.g., //server/share)
#   $2 - Drive letter (e.g., Z:)
# =============================================================================
mount_windows() {
    local smb_share="$1"
    local mount_drive="$2"
    
    # Default drive letter if not specified
    local drive_letter="${mount_drive:-Z:}"
    
    # Check if the drive is already mapped
    if net use "$drive_letter" >/dev/null 2>&1; then
        echo "Drive $drive_letter is already in use. Unmapping..."
        net use "$drive_letter" /delete
    fi
    
    # Map the SMB share to the drive letter as guest
    echo "Mapping SMB share $smb_share to drive $drive_letter..."
    net use "$drive_letter" "$smb_share" /user:guest /persistent:no
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
    DEFAULT_MOUNT_POINT="/mnt/irds"
    mount_linux "$SMB_SHARE" "$DEFAULT_MOUNT_POINT"
    NAS_MOUNT_PATH="$DEFAULT_MOUNT_POINT"
    ;;
  darwin*)
    echo "Detected macOS."
    mount_macos "$SMB_SHARE"
    ;;
  cygwin* | msys* | win32*)
    echo "Detected Windows OS."
    # Specify the drive letter; default is Z:
    DEFAULT_MOUNT_DRIVE="Z:"
    mount_windows "$SMB_SHARE" "$DEFAULT_MOUNT_DRIVE"
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
    # Fetch the health status of the container
    container_status=$(docker inspect --format='{{.State.Health.Status}}' cits3200-project-web-1 2>/dev/null)
    
    if [ "$container_status" = "healthy" ]; then
        echo "Docker container is healthy and running."
        break
    elif [ "$container_status" = "unhealthy" ]; then
        echo "Docker container is unhealthy. Check logs for details."
        docker logs cits3200-project-web-1
        exit 1
    elif [ -z "$container_status" ]; then
        echo "Error: Container 'cits3200-project-web-1' not found. Ensure the service name is correct."
        exit 1
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

