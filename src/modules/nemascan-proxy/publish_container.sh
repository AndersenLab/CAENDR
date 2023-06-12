#!/bin/bash

set +a
set -e

reload_git=''
tag=''

print_usage() {
  printf "Usage: %s [-r (reload_git)] -t tag_name" $0;
}


# Get command line arguments
while getopts 'rt:h' flag; do
  case "${flag}" in
    r) reload_git='true' ;;
    t) tag="${OPTARG}" ;;
    h) print_usage
       exit 0 ;;
    *) print_usage
       exit 1 ;;
  esac
done


# Get current environment
if [ -z ${ENV+x} ]; then
    echo "Must set var ENV";
    exit 1;
fi
echo "ENV is set to '$ENV'";


# Get GCP project from env file
source ../../../env/${ENV}/global.env
if [ -z ${GOOGLE_CLOUD_PROJECT_ID+x} ]; then
    echo "Env file '../../../env/${ENV}/global.env' must define a variable 'GOOGLE_CLOUD_PROJECT_ID'";
    exit 1;
fi
echo "Using GCP project ${GOOGLE_CLOUD_PROJECT_ID}"


# Ensure container tag passed as argument
if [ -z ${tag} ]; then
    echo "Must provide value for tag";
    exit 1;
fi
echo "Publishing with tag '${tag}'";


# Clone git project
if [ -n "${reload_git}" ]; then
    rm -rf ./NemaScan
fi
git clone --depth 1 git@github.com:northwestern-mti/NemaScan.git


# Build and push container
docker build --no-cache --platform linux/amd64 -t gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/nemascan-nxf:${tag} -f NemaScan/Dockerfile ./NemaScan
docker push gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/nemascan-nxf:${tag}
