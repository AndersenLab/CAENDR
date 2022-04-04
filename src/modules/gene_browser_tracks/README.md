# Gene Browser Tracks
## src/modules/gene_browser_tracks
-------------------------------------------------------------------
This directory contains the code to build the gene_browser_tracks container which generates the tracks used by the IGV Gene Browser plugin from the external wormbase gene database

Gene track generation requests are scheduled in the Cloud Tasks Queue through the web admin portal, then executed by the api-pipeline-task module to prevent timeouts.

The version of wormbase data to use is configured by defining the WORMBASE_VERSION environment variable. The Cloud Storage destination of the generated tracks can optionally be set by defining the BROWSER_BUCKET_NAME and BROWSER_BLOB_PATH environment variables, otherwise the default values will be used.

examples:

```bash
export WORMBASE_VERSION=WS282
export BROWSER_BUCKET_NAME=destination-bucket
export BROWSER_BLOB_PATH=browsertracks/WS282/
/gene_browser_tracks/run.sh
```

```bash
export WORMBASE_VERSION=281
/gene_browser_tracks/run.sh
```

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
    * Update `version` in the file `src/modules/gene_browser_tracks/module.env`. 

3. Move to the module folder and configure the module for deployment:
    ```bash
    cd src/modules/gene_browser_tracks
    make configure
    ```
    * The module root folder should now contain a *.env* file
    * The module root folder SHOULD NOT contain a *venv* folder

4. Publish the module to GCR:
    ```bash
    make publish
    ```
    * When the command completes, check the [GCR](https://console.cloud.google.com/gcr/images/caendr/global/caendr-gene-browser-tracks?authuser=1&project=caendr) and confirm your image with the proper version tag is appearing

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
    terraform plan -target module.gene_browser_tracks -out tf_plan && terraform apply tf_plan
    ```