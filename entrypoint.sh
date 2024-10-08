#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print commands and their arguments as they are executed


# Wait for the database to be ready
# Adjust the host and port according to your database configuration
# For example, if using PostgreSQL and the service is named 'db'
while ! nc -z db 5432; do
  echo "Waiting for the database..."
  sleep 1
done

echo "Database is up and running!"

# Apply database migrations
flask db upgrade

# Start the Flask application
exec flask run --host=0.0.0.0

