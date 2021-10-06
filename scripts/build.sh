#!/bin/bash

# usage: ./build.sh PROJECT_ID BASE_IMAGE_NAME
docker buildx build --platform linux/amd64 -t gcr.io/$1/$2:latest ./firebase