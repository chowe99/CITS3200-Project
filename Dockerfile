# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y netcat-openbsd libpq-dev build-essential && \
    rm -rf /var/lib/apt/lists/*
# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy and set permissions for the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port 5000 for the Flask app
EXPOSE 5000

# Run the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
