#!/bin/bash

# usage: ./push.sh PROJECT_ID BASE_IMAGE_NAME
docker tag gcr.io/$1/$2:latest grc.io/$1/$2:latest
docker push gcr.io/$1/$2:latest