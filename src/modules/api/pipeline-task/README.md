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
Targeted deployment is under construction until isolated TF states can be establish for each module.

See full app deployment docs in the [root project README.md](../../../../README.md#deployment).

<!-- Pre-requisites: 
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
    ``` -->

## Architecture Diagram
-------------------------------------------------------------------
![Architecture Diagram](pipeline_task_execution.png)


## Pipeline Sample Requests

Route: /start/{task_route}
Where `task_route` is one of the following values: 

* `db-ops` - DatabaseOperationTask(payload)
* `nscalc` - NemaScanTask(payload)
* `ipcalc` - IndelPrimerTask(payload)
* `h2calc` - HeritabilityTask(payload)
* `gene-browser-tracks` - GeneBrowserTracks(payload)

### Heritability

#### Pipeline Status
POST /task/status

Payload:
```
{
    "message":{
        "attributes": {
            "operation": "projects/[GOOGLE_PROJECT_ID]/locations/us-central1/operations/[OPERATION_ID]"
        }
    }
}
```

NOTE: Fields in square brackets are redacted. 
Sample Error Response: 
```
{
  "name": "projects/[GOOGLE_PROJECT_ID]/locations/us-central1/operations/[OPERATION_ID]",
  "metadata": {
    "@type": "type.googleapis.com/google.cloud.lifesciences.v2beta.Metadata",
    "pipeline": {
      "actions": [
        {
          "containerName": "heritability-[DATA_HASH]",
          "imageUri": "[CONTAINER_NAME]:[CONTAINER_VERSION]",
          "commands": [
            "./heritability-nxf.sh"
          ],
          "environment": {
            "WORK_DIR": "gs://[REDACTED__BUCKET_NAME]/[REDACTED_DATA_HASH]",
            "GOOGLE_ZONE": "[GOOGLE_ZONE]",
            "GOOGLE_PROJECT": "[GOOGLE_PROJECT_ID]",
            "VCF_VERSION": "20220216",
            "DATA_BUCKET": "[BUCKET_NAME]",
            "TRAIT_FILE": "[BUKCET_NAME]/reports/heritability/[CONTAINER_VERSION]/[DATA_HASH]/data.tsv",
            "DATA_HASH": "[DATA_HASH]",
            "DATA_BLOB_PATH": "reports/heritability/[CONTAINER_VERSION]/[DATA_HASH]",
            "GOOGLE_SERVICE_ACCOUNT_EMAIL": "[SERVICE_ACCOUNT_EMAIL_ADDRESS]",
            "OUTPUT_DIR": "gs://[BUKCET_NAME]/reports/heritability/[CONTAINER_VERSION]/[DATA_HASH]"
          },
          "timeout": "9000s"
        }
      ],
      "resources": {
        "zones": [
          "us-central1-a"
        ],
        "virtualMachine": {
          "machineType": "n1-standard-1",
          "labels": {
            "goog-pipelines-worker": "true"
          },
          "serviceAccount": {
            "email": "[SERVICE_ACCOUNT_EMAIL_ADDRESS]",
            "scopes": [
              "https://www.googleapis.com/auth/cloud-platform"
            ]
          },
          "bootDiskSizeGb": 10,
          "bootImage": "projects/cos-cloud/global/images/family/cos-stable",
          "nvidiaDriverVersion": "450.51.06",
          "enableStackdriverMonitoring": true
        }
      },
      "timeout": "9000s"
    },
    "events": [
      {
        "timestamp": "2023-02-24T21:01:07.814651908Z",
        "description": "Worker released",
        "workerReleased": {
          "zone": "us-central1-a",
          "instance": "google-pipelines-worker-[WORKER_ID]"
        }
      },
      {
        "timestamp": "2023-02-24T21:01:07.263988705Z",
        "description": "Execution failed: generic::failed_precondition: while running \"heritability-7ca074fbac0b4f8c90a40eb864429768\": unexpected exit status 1 was not ignored",
        "failed": {
          "code": "FAILED_PRECONDITION",
          "cause": "Execution failed: generic::failed_precondition: while running \"heritability-7ca074fbac0b4f8c90a40eb864429768\": unexpected exit status 1 was not ignored"
        }
      },
      {
        "timestamp": "2023-02-24T21:01:07.230111520Z",
        "description": "Unexpected exit status 1 while running \"heritability-7ca074fbac0b4f8c90a40eb864429768\"",
        "unexpectedExitStatus": {
          "actionId": 1,
          "exitStatus": 1
        }
      },
      {
        "timestamp": "2023-02-24T21:01:07.230103909Z",
        "description": "Stopped running \"heritability-7ca074fbac0b4f8c90a40eb864429768\": exit status 1",
        "containerStopped": {
          "actionId": 1,
          "exitStatus": 1
        }
      },
      {
        "timestamp": "2023-02-24T21:00:44.068364130Z",
        "description": "Started running \"heritability-7ca074fbac0b4f8c90a40eb864429768\"",
        "containerStarted": {
          "actionId": 1
        }
      },
      {
        "timestamp": "2023-02-24T21:00:41.553112938Z",
        "description": "Stopped pulling \"andersenlab/heritability:v0.3\"",
        "pullStopped": {
          "imageUri": "andersenlab/heritability:v0.3"
        }
      },
      {
        "timestamp": "2023-02-24T20:59:27.249417257Z",
        "description": "Started pulling \"andersenlab/heritability:v0.3\"",
        "pullStarted": {
          "imageUri": "andersenlab/heritability:v0.3"
        }
      },
      {
        "timestamp": "2023-02-24T20:58:48.542631851Z",
        "description": "Worker \"google-pipelines-worker-[WORKER_ID]\" assigned in \"us-central1-a\" on a \"n1-standard-1\" machine",
        "workerAssigned": {
          "zone": "us-central1-a",
          "instance": "google-pipelines-worker-[WORKER_ID]",
          "machineType": "n1-standard-1"
        }
      }
    ],
    "createTime": "2023-02-24T20:58:33.788877Z",
    "startTime": "2023-02-24T20:58:48.542631851Z",
    "endTime": "2023-02-24T21:01:07.814651908Z",
    "pubSubTopic": "[PUBSUB_TOPIC]"
  },
  "done": true,
  "error": {
    "code": 9,
    "message": "Execution failed: generic::failed_precondition: while running \"heritability-7ca074fbac0b4f8c90a40eb864429768\": unexpected exit status 1 was not ignored"
  }
}
```




### Other

Method: POST

*Payload Schema*
```
{
    id: string,
    kind: string,
    container_name: string,
    container_version: string,
    container_repo: string,
    username: string [optional],
    email: string [optional],
    data_hash: string [optional: IndelPrimerTask],
    strain_1: string [optional: IndelPrimerTask],
    strain_2: string [optional: IndelPrimerTask],
    site: string [optional: IndelPrimerTask],
    wormbase_version: string [optional: GeneBrowserTracksTask],
    args: any [optional],
}
```

Where:
`id` is the value of the DataStore `key` entity. 
`kind` is the datastore kind
`username` is the CaeNDR username starting this task (useful for email notifications)
`email` is the CaeNDR email of the user initiating the task (useful for email notifications)
`container_name` is the name of the GCR container (within the project)
`container_version` maps to container tags
`container_repo` maps to the container registry. Most are `gcr` or `dockerhub`

Note: `image_uri = f"{task.container_repo}/{task.container_name}:{task.container_version}"`

*Payload Example*

URI: /start/h2calc
Method: POST
Payload:
```
{
    id: "123",
    kind: "",
    username: "erik",
    email: "mockemail@mockcompany.com"
    container_name: "",
    container_version: "",
    container_repo: "",
}
```
