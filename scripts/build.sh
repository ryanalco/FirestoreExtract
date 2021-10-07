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