# CeNDR Lifesciences Pipeline Task Runner

## src/modules/api/pipeline-task
-------------------------------------------------------------------
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

=============================================================================
## Deploying
-------------------------------------------------------------------
Pre-requisites: 
Ensure that you are logged in to the GCLOUD GCP project in the CLI, or using a devops service account.

Open a terminal at the root of the project:
1. Set ENV and GOOGLE_APPLICATION_CREDENTIALS environment variables:
    ```bash
    export ENV={ENV_TO_DEPLOY}
    export GOOGLE_APPLICATION_CREDENTIALS={PATH_TO_GCP_CREDENTIALS}
    ```
2. Increment the versions for the module:
    * Update the `version` property for the site in the `/env/{env}/global.env` .
    * Update `version` in the file `src/modules/api/pipeline-task/module.env`. 

3. Move to the module folder and configure the module for deployment:
    ```bash
    cd src/modules/api/pipeline-task
    make configure
    ```
    * The module root folder should now contain a *.env* file
    * The module root folder SHOULD NOT contain a *venv* folder

4. Publish the module to GCR:
    ```bash
    make publish
    ```
    * When the command completes, check the [GCR](https://console.cloud.google.com/gcr/images/caendr/global/caendr-api-pipeline-task?authuser=1&project=caendr) and confirm your image with the proper version tag is appearing

5. Deploy in Terraform shell:
    * Pull down existing terraform state
    ```bash
    make cloud-resource-init
    ```
    * Open a terraform-shell
    ```bash
    make terraform-shell
    ```
    * Create a plan targeting the module and apply the plan
    ```bash
    terraform plan -target module.api_pipeline_task -out tf_plan && terraform apply tf_plan
    ```

## Architecture Diagram
-------------------------------------------------------------------
![Architecture Diagram](pipeline_task_execution.png)
