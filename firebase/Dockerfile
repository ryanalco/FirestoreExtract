# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9-slim

ARG BUCKET_NAME="popl-test-bucket-123"

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME

COPY requirements.txt ./requirements.txt

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

ADD keys ./keys
COPY firebase.py ./firebase.py
COPY main.py ./main.py

# Set environment variables
ENV BUCKET_NAME=${BUCKET_NAME}
ENV SERVICE_ACCOUNT_PATH="${APP_HOME}/keys/keyfile.json"
ENV POPL_SERVICE_ACCOUNT_PATH="${APP_HOME}/keys/serviceAccountKey.json"

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
