#!/bin/bash

GIT_URL=git@github.com:northwestern-mti/calc_heritability.git 
GIT_BRANCH=main

echo "Env: ${ENV}"

if [ -z "$ENV" ]; then
    echo "Missing ENV variable".
    exit
fi

# load caendr env
set +a
source ../../../env/${ENV}/global.env

# this requires reading the respective global.env above
IMAGE_URI=gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${HERITABILITY_CONTAINER_NAME}:${HERITABILITY_CONTAINER_VERSION}

if [ -d calc_heritability] ]; then
    echo "Found cloned repo: $GIT_REPO_URL."
else
    git clone -b $GIT_BRANCH --depth 1 $GIT_URL
fi

if [ "Darwin" == uname ]; then
    docker buildx build --platform=linux/amd64 --no-cache -t $IMAGE_URI -f calc_heritability/Dockerfile ./calc_heritability
else
    docker build --no-cache -t $IMAGE_URI -f calc_heritability/Dockerfile ./calc_heritability
fi

echo "push to $IMAGE_URI? (CTRL+C to cancel)?"
read

docker push $IMAGE_URI
