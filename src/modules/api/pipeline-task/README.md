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

## Deploying
Open a terminal at the root of the project:
1. Set ENV and GOOGLE_APPLICATION_CREDENTIALS environment variables:
    ```
    export ENV={ENV_TO_DEPLOY}

    export GOOGLE_APPLICATION_CREDENTIALS={PATH_TO_GCP_CREDENTIALS}
    ```
2. Increment the versions for the module:
    * env/{ENV}/global.env > MODULE_API_PIPELINE_TASK_CONTAINER_VERSION
    * src/modules/api/pipeline-task/module.env > MODULE_VERSION

3. Deploy in Terraform shell:
    ```
    make cloud-resource-init
    
    make terraform-shell
    
    terraform plan -target module.api_pipeline_task -out tf_plan && terraform apply tf_plan
    ```

## Architecture Diagram

![Architecture Diagram](pipeline_task_execution.png)
