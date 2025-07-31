#!/bin/bash


# Base Docker Image spawn by google lifesciences to run nextflow pipeline
# same image is used by each environment (DEV/TEST/PROD)
VERSION=v0.01
IMAGE_URI=andersenlab/heritability-gls-base:${VERSION}
GIT_URL=https://github.com/andersenlab/calc_heritability
# NOTE: GIT_BRANCH can be a branch, tag, or commit hash
GIT_BRANCH=release_20250625

echo "Make sure to login to docker hub via CLI before running this script"
echo "Example: \$ docker login"

# checkout the repository.
if [ ! -d "calc_heritability" ]; then
   git clone --depth 1 -b "${GIT_BRANCH}" "${GIT_URL}"
fi

# build docker image for /env/Dockerfile
if [[ $OSTYPE == "darwin"* ]]; then
    echo "docker buildx build --platform=linux/amd64 --no-cache -t $IMAGE_URI -f calc_heritability/env/Dockerfile ./calc_heritability/env"
    docker buildx build --platform=linux/amd64 --no-cache -t $IMAGE_URI -f calc_heritability/env/Dockerfile ./calc_heritability/env
else
    echo "docker build --no-cache -t $IMAGE_URI -f calc_heritability/env/Dockerfile ./calc_heritability/env"
    docker build --no-cache -t $IMAGE_URI -f calc_heritability/env/Dockerfile ./calc_heritability/env
fi

# push image
echo "push to ${IMAGE_URI}? (CTRL+C to cancel)"
read
docker push $IMAGE_URI
