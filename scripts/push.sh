#!/bin/bash

PROJECT_ID=$1
BASE_IMAGE_NAME=$2

# usage: ./push.sh PROJECT_ID BASE_IMAGE_NAME
docker tag gcr.io/${PROJECT_ID}/${BASE_IMAGE_NAME}:latest grc.io/${PROJECT_ID}/${BASE_IMAGE_NAME}:latest
docker push gcr.io/${PROJECT_ID}/${BASE_IMAGE_NAME}:latest