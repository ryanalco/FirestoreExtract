#!/bin/bash

# usage: ./build-tag-push.sh PROJECT_ID BASE_IMAGE_NAME
docker build -t gcr.io/$1/$2:latest ./firebase
docker tag gcr.io/$1/$2:latest grc.io/$1/$2:latest
docker push gcr.io/$1/$2:latest