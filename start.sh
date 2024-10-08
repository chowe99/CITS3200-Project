#!/bin/bash

# Function to handle cleanup on exit (Ctrl+C)
cleanup() {
    echo "Stopping Docker container..."
    docker-compose down
    echo "Docker container stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT) and call cleanup
trap cleanup SIGINT

# Check if NAS_MOUNT_PATH argument is provided, fallback to environment variable
if [ -z "$1" ]; then
    if [ -z "$NAS_MOUNT_PATH" ]; then
        echo "Error: NAS_MOUNT_PATH argument not provided and environment variable NAS_MOUNT_PATH is not set."
        echo "Usage: ./start.sh <NAS_MOUNT_PATH> or ensure \$NAS_MOUNT_PATH is set in the environment."
        exit 1
    else
        echo "Using NAS_MOUNT_PATH from environment: $NAS_MOUNT_PATH"
    fi
else
    NAS_MOUNT_PATH=$1
    echo "Using NAS_MOUNT_PATH from argument: $NAS_MOUNT_PATH"
fi

# Export NAS_MOUNT_PATH to be used in Docker Compose
export NAS_MOUNT_PATH

# Start Docker Compose and wait for it to become healthy
echo "Starting Docker container..."
NAS_MOUNT_PATH=$NAS_MOUNT_PATH docker-compose up -d 

# Wait for the container to become healthy
echo "Waiting for the Docker container to be healthy..."
while true; do
    sleep 5
    container_status=$(docker inspect --format='{{.State.Health.Status}}' cits3200-project-web-1)

    if [ "$container_status" = "healthy" ]; then
        echo "Docker container is healthy and running."
        break
    elif [ "$container_status" = "unhealthy" ]; then
        echo "Docker container is unhealthy. Check logs for details."
        docker logs cits3200-project-web-1
        exit 1
    else
        echo "Still waiting for container to become healthy..."
    fi
done

# Determine the OS and open the browser
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://127.0.0.1:5123  # Linux
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open http://127.0.0.1:5123  # macOS
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    start http://127.0.0.1:5123  # Windows
else
    echo "OS not recognized. Please manually open the browser at http://127.0.0.1:5123"
fi

# Keep the script running to allow cleanup on Ctrl+C
while :; do
    sleep 1
done

