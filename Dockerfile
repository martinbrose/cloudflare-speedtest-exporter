# Use an official Python runtime based on Alpine Linux as a parent image
FROM python:3.12.4-alpine3.19

# Create a new user 'speedtest' to run the application
# This is a good practice to avoid running the application with root privileges
RUN adduser -D speedtest

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents (src folder) into the container at /app
COPY src/. .

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Don't store the cache of pip packages. Helps to reduce image size
# find command: Delete all compiled Python files. This helps to reduce image size
RUN pip install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.12 -name "*.pyc" -type f -delete

# Change to the 'speedtest' user
# This is a good practice to avoid running the application with root privileges
USER speedtest

# Run exporter.py when the container launches
CMD ["python", "-u", "exporter.py"]

# Healthcheck instruction to check the health of the application
# wget command: Check if the application is serving on the expected port
# --no-verbose: Turn off wget's output
# --tries=1: Set number of retries to 1 before failing
# --spider: Don't download the files, just check that they are there
HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${SPEEDTEST_PORT:=9798}/