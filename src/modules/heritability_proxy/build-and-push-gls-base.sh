#!/bin/bash


# Base Docker Image spawn by google lifesciences to run nextflow pipeline
# same image is used by each environment (DEV/TEST/PROD)
IMAGE_URI=northwesternmti/heritability-gls-base:latest
GIT_URL=https://northwestern-mti/calc_heritability
# NOTE: GIT_BRANCH can be a branch, tag, or commit hash
GIT_BRANCH=3bad69ff3c56681ab00fa970e45b7a3268ac2a4d

echo "Make sure to login to docker hub via CLI before running thiis script"
echo "Example: \$ docker login"

# checkout the repository.
if [ ! -d "calc_heritability" ]; then
   git clone --depth 1 -b "${GIT_BRANCH}" "${GIT_URL}"
fi

# build docker image for /env/Dockerfile
if [ "Darwin" == uname ]; then
    docker buildx build --platform=linux/amd64 --no-cache -t $IMAGE_URI -f calc_heritability/env/Dockerfile ./calc_heritability/env
else
    docker build --no-cache -t $IMAGE_URI -f calc_heritability/env/Dockerfile ./calc_heritability/env
fi

# push image
echo "push to ${IMAGE_URI}? (CTRL+C to cancel)"
read
docker push $IMAGE_URI
