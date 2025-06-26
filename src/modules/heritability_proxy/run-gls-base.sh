#!/bin/bash

set +a

if [ -z $ENV ]; then
	echo "Missing ENV".
  exit
fi
echo "Env: ${ENV}"
source ../../../env/${ENV}/global.env

IMAGE_URI=us-east4-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT_ID}/caendr-site-v2/heritability:v0.04

docker pull $IMAGE_URI

docker run -it \
	--env-file sample.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secret \
  -v PATH_TO_MY_SERVICE_ACCOUNT_JSON:/secret \
  $IMAGE_URI \
  /bin/bash
