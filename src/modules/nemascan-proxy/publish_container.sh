#!/bin/bash

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
else
    echo "ENV is set to '$ENV'";
fi

# Map environment to GCP project
if [ $ENV = "qa" ]; then
    gcp_project_id="mti-caendr"
elif [ $ENV = "development" ]; then
    gcp_project_id="andersen-lab-dev-330218"
else
    echo "Invalid ENV '$ENV'"
    exit 1;
fi
echo "Using GCP project ${gcp_project_id}"

# Ensure container tag passed as argument
if [ -z ${tag} ]; then
    echo "Must provide value for tag";
    exit 1;
else
    echo "Publishing with tag '${tag}'";
fi


set +a
source ../../../env/${ENV}/global.env

if [ -n "${reload_git}" ]; then
    rm -rf ./NemaScan
fi
git clone --depth 1 git@github.com:northwestern-mti/NemaScan.git


docker build --no-cache --platform linux/amd64 -t gcr.io/${gcp_project_id}/nemascan-nxf:${tag} -f NemaScan/Dockerfile ./NemaScan
docker push gcr.io/${gcp_project_id}/nemascan-nxf:${tag}
