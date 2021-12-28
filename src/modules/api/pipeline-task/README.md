# CeNDR Lifesciences Pipeline Task Runner

Requirements:
python3
python3-venv
virtualenv
python3-virtualenv
google-cloud-sdk

gcloud auth configure-docker

Removing cached project files:
make clean

Setting up local environment for testing:
make venv

Running locally:
make run

Write terraform config vars file
Apply global env config to service level .env file
Merge service level env config
write cloudbuild file:
make configure

build container image:
make build

test container
make run-container

build container in the cloud and publish as latest version:
make cloudbuild

## Architecture Diagram

![Architecture Diagram](pipeline_task_execution.png)
