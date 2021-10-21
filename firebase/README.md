# Firebase to GCP Bucket Cloud Run Service

## Containerizing a Service

Google Cloud Run runs a containerized service. This container is triggered by HTTP requests and should respect the [container contract](https://cloud.google.com/run/docs/reference/container-contract). Essentially, the service must be run as a web service that listens for HTTP requests and runs a job when triggered. Here is an example of how to create a very simple service:

### Containerize the Service

1. Create a `main.py` file:

    ```python
    import os

    from flask import Flask

    from some_module import run_service

    app = Flask(__name__)


    @app.route("/")
    def index():
        run_service()
        return ("", 204)


    if __name__ == "__main__":
        app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    ```

2. Create a file named `requirements.txt` and add any dependencies to the service here. In this example:

    ```txt
    Flask==2.0.1
    gunicorn==20.1.0
    ```

3. Create a Dockerfile that starts a Gunicorn web server that listens on the port defined by the PORT environment variable:

    ```Dockerfile
    # Use the official lightweight Python image.
    # https://hub.docker.com/_/python
    FROM python:3.9-slim

    # Allow statements and log messages to immediately appear in the Knative logs
    ENV PYTHONUNBUFFERED True

    # Copy local code to the container image.
    ENV APP_HOME /app
    WORKDIR $APP_HOME
    COPY . ./

    # Install production dependencies.
    RUN pip install --no-cache-dir -r requirements.txt

    # Run the web service on container startup. Here we use the gunicorn
    # webserver, with one worker process and 8 threads.
    # For environments with multiple CPU cores, increase the number of workers
    # to be equal to the cores available.
    # Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
    CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
    ```

4. Add a `.dockerignore` file to exclude files from your container image.

    ```.dockerignore
    Dockerfile
    README.md
    *.pyc
    *.pyo
    *.pyd
    __pycache__
    .pytest_cache
    ```

### Build Image and Push to Registry

Once the Dockerfile is created, you will need to build the image and push it to a container registry so that Google Cloud Run can retrieve it and run the service.

> **Note**: These commands should be run from the root of the repo

1. Build the image:

    ```bash
    docker buildx build --platform linux/amd64 -t gcr.io/<PROJECT_ID>/<IMAGE_NAME>:latest ./firebase
    ```

2. Tag and Push the image to [GCR](https://cloud.google.com/container-registry)

    ```bash
    docker tag gcr.io/<PROJECT_ID>/<IMAGE_NAME>:latest grc.io/<PROJECT_ID>/<IMAGE_NAME>:latest
    docker push gcr.io/<PROJECT_ID>/<IMAGE_NAME>:latest
    ```

## Deploying a New Service

1. Create a new `service.yml` file with this content:

    ```yml
    apiVersion: serving.knative.dev/v1
    kind: Service
    metadata:
    name: <SERVICE>
    spec:
    template:
        spec:
        containers:
        - image: <IMAGE URL>
    ```

2. Deploy the new service using the following command:

    ```bash
    gcloud run services replace service.yaml --region=<REGION>
    ```

## Running Service on a Schedule

1. Create a service account to associate with Cloud Scheduler

    ```bash
    gcloud iam service-accounts create firebase-extract-invoker \
    --display-name "firebase-extract-invoker"
    ```

2. Give service account permission to invoke service

    ```bash
    gcloud run services add-iam-policy-binding popl-firebase-extractor \
    --member=serviceAccount:firebase-extract-invoker@poplco.iam.gserviceaccount.com \
    --role=roles/run.invoker
    ```

3. Create job that invokes your service at specified interval (example shows invoking every day at 1am)

    ```bash
    gcloud scheduler jobs create http invoke-firebase-extractor --schedule "0 1 * * *" \
    --http-method=GET \
    --uri=$1 \
    --oidc-service-account-email=$2\
    --oidc-token-audience=$1
    ```

    Where `$1` = the service url and `$2` = the service account email address

    > **Hint**: you can run the following command to get the service account email address:
    > `gcloud iam service-accounts list`

## Firebase

### Code

The `get_collection_documents` function in the [firebase.py](firebase/firebase.py) is the function that creates a firebase query. This is where you can update the query as needed.

### Environment Variables

The firebase service is built using a [Dockerfile](firebase/Dockerfile). The Dockerfile has `ARG`s defined near the top of the file which populate environment variables in the container which the `firebase.py` code uses. These need to be updated with the approriate env vars. Alternatively, using `ARG`s also allows these values to be overwritten when building the container. Example:

```bash
docker buildx build --platform linux/amd64 -t \
    --build-arg BUCKET_NAME=<MY_BUCKET_NAME> \
    --build-arg MAX_RUN_TIME=3600 \
    gcr.io/<PROJECT_ID>/<IMAGE_NAME>:latest ./firebase
```

## Using Scripts

I have provided some simple bash scripts to help with the different steps needed to build, tag, and push a docker image to gcr as well as scripts for deploying the service to Cloud Run and creating the schedule. These scripts have variables at the top of the file that can be passed to the script when running. Example, take a look at the [build.sh](scripts/build.sh) script:

```bash
#!/bin/bash

PROJECT_ID=$1
BASE_IMAGE_NAME=$2
BUCKET=$3
DEFAULT_BATCH_SIZE=$4
MAX_RUN_TIME=$5

# usage: ./build.sh PROJECT_ID BASE_IMAGE_NAME BUCKET DEFAULT_BATCH_SIZE MAX_RUN_TIME
docker buildx build --platform linux/amd64 \
    --build-arg BUCKET=${BUCKET} \
    --build-arg DEFAULT_BATCH_SIZE=${DEFAULT_BATCH_SIZE} \
    --build-arg MAX_RUN_TIME=${MAX_RUN_TIME} \
    -t gcr.io/${PROJECT_ID}/${BASE_IMAGE_NAME}:latest ./firebase
```

This could be run like so (from the root of the repo):

```bash
bash scripts/build.sh poplco firebase-extractor popl-firebase-collections 1000 600
```

Where each argument after `scripts/build.sh` is an argument that is mapped in order to each variable defined at the top of the script. "poplco" would equate to `$1`, "firebase-extractor" would be `$2`, etc...
