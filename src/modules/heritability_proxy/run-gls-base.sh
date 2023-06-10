#!/bin/bash

set +a

if [ -z $ENV ]; then
	echo "Missing ENV".
  exit
fi
echo "Env: ${ENV}"
source ../../../env/${ENV}/global.env

IMAGE_URI=gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/heritability:v0.02-debug

docker pull $IMAGE_URI

docker run -it \
	--env-file sample.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secret \
  -v PATH_TO_MY_SERVICE_ACCOUNT_JSON:/secret \
  $IMAGE_URI \
  /bin/bash
