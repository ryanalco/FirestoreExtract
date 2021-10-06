#!/bin/bash

# usage: bash create-scheduler.sh SERVICE_URL SERVICE_ACCOUNT_EMAIL
gcloud scheduler jobs create http invoke-firebase-extractor --schedule "0 1 * * *" \
   --http-method=GET \
   --uri=$1 \
   --oidc-service-account-email=$2\
   --oidc-token-audience=$1