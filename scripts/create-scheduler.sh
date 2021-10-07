#!/bin/bash

SERVICE_URL=$1
SERVICE_ACCOUNT_EMAIL=$2

# usage: bash create-scheduler.sh SERVICE_URL SERVICE_ACCOUNT_EMAIL
gcloud scheduler jobs create http invoke-firebase-extractor --schedule "0 4 * * *" \
   --http-method=GET \
   --uri=${SERVICE_URL} \
   --oidc-service-account-email=${SERVICE_ACCOUNT_EMAIL} \
   --oidc-token-audience=${SERVICE_URL}