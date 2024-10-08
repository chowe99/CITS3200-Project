#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print commands and their arguments as they are executed

# Do not run migrations
# flask db upgrade

# Check if NAS is mounted
if ! mountpoint -q /mnt/nas; then
  echo "NAS drive is not mounted at /mnt/nas. Please mount the NAS drive and restart the container."
  exit 1
fi

exec flask run --host=0.0.0.0
