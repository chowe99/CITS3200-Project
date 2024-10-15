#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print commands and their arguments as they are executed

# Do not run migrations
# flask db upgrade

exec flask run --host=0.0.0.0 --port=5123

