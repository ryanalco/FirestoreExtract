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
COPY main.py ./main.py

# Set environment variables
ENV BUCKET_NAME=${BUCKET_NAME}
ENV SERVICE_ACCOUNT_PATH="${APP_HOME}/keys/keyfile.json"
ENV POPL_SERVICE_ACCOUNT_PATH="${APP_HOME}/keys/serviceAccountKey.json"

# Expose port for google cloud
EXPOSE 8080

CMD python main.py
