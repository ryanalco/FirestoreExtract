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
