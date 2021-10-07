#!/bin/bash

REGION=$1

# usage: bash scripts/deploy_to_cloud_run.sh REGION
gcloud run services replace service.yml --region=${REGION}
