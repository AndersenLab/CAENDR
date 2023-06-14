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

# Get env file
env_file="../../../env/${ENV}/global.env"
source ${env_file}


# Ensure GCP project defined in env file
if [ -z ${GOOGLE_CLOUD_PROJECT_ID+x} ]; then
    echo "Env file '${env_file}' must define a variable 'GOOGLE_CLOUD_PROJECT_ID'";
    exit 1;
fi

# Ensure container name defined in env file
if [ -z ${NEMASCAN_NXF_CONTAINER_NAME+x} ]; then
    echo "Env file '${env_file}' must define a variable 'NEMASCAN_NXF_CONTAINER_NAME'";
    exit 1;
fi

# Ensure GitHub organization & repo defined in env file
if [ -z ${NEMASCAN_SOURCE_GITHUB_ORG+x} ]; then
    echo "Env file '${env_file}' must define a variable 'NEMASCAN_SOURCE_GITHUB_ORG'";
    exit 1;
fi
if [ -z ${NEMASCAN_SOURCE_GITHUB_REPO+x} ]; then
    echo "Env file '${env_file}' must define a variable 'NEMASCAN_SOURCE_GITHUB_REPO'";
    exit 1;
fi

# Print env vars
echo "Using GCP project ${GOOGLE_CLOUD_PROJECT_ID}"
echo "Using GitHub project ${NEMASCAN_SOURCE_GITHUB_ORG}/${NEMASCAN_SOURCE_GITHUB_REPO}"


# Ensure container tag passed as argument
if [ -z ${tag} ]; then
    echo "Must provide value for tag";
    exit 1;
fi
echo "Publishing with tag '${tag}'";


# Clone git project
if [ -n "${reload_git}" ]; then
    rm -rf ./${NEMASCAN_SOURCE_GITHUB_REPO}
fi
git clone --depth 1 git@github.com:${NEMASCAN_SOURCE_GITHUB_ORG}/${NEMASCAN_SOURCE_GITHUB_REPO}.git


# Build and push container
echo "Building container gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${NEMASCAN_NXF_CONTAINER_NAME}:${tag}"
docker build --no-cache --platform linux/amd64 -t gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${NEMASCAN_NXF_CONTAINER_NAME}:${tag} -f ${NEMASCAN_SOURCE_GITHUB_REPO}/Dockerfile ./${NEMASCAN_SOURCE_GITHUB_REPO}
docker push gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${NEMASCAN_NXF_CONTAINER_NAME}:${tag}
