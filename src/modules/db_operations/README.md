# Database Operations
## src/modules/db_operations
-------------------------------------------------------------------
This directory contains the code to build the caendr-db-operations container which contains tools for performing long running database operations.

Database operations are scheduled in the Cloud Tasks Queue through the web admin portal, then executed by the api-pipeline-task module to prevent timeouts.

The operation to be performed is configured by defining the DATABASE_OPERATION environment variable and any arguments that may need to provided to that operation are defined using additional environment variables.

examples:

- OP_NAME:
  - ARG_NAME1
  - ARG_NAME2

export DATABASE_OPERATION=OP_NAME
export ARG_NAME1=argument value
export ARG_NAME2=another argument value
run.sh

- ALT_OP:

export DATABASE_OPERATION=ALT_OP
run.sh

=============================================================================
## Operations
-------------------------------------------------------------------
- DROP_AND_POPULATE_ALL_TABLES:
  - WORMBASE_VERSION
  - STRAIN_VARIANT_ANNOTATION_VERSION
- DROP_AND_POPULATE_STRAINS:
- DROP_AND_POPULATE_WORMBASE_GENES:
  - WORMBASE_VERSION
- DROP_AND_POPULATE_STRAIN_ANNOTATED_VARIANTS:
  - STRAIN_VARIANT_ANNOTATION_VERSION

=============================================================================

## Deploying
-------------------------------------------------------------------
Targeted deployment is under construction until isolated TF states can be establish for each module.

See full app deployment docs in the [root project README.md](../../../README.md#deployment).


___

## Troubleshooting ETL operations

To troubleshoot the ETL operations, instead of running the operations against the production postgres, we can run against a local SQLITE database that runs in memory. The main reason to do this is speed. Please note that the sqlite memory is only available while the python is running. Consider changing the SQLITE to a local file if temporary persistence of the Sqlite data is needed. 

Activate Step-by-Step of the ETL operations: 

In the terminal, run:
```
export ENV=main
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/YOUR_FILE_HERE

cd src/modules/db_operations
make clean-venv
make venv
code ../../..
```

In VSCode:

* Check that the Debug Launch for DROP_AND_POPULATE_ALL_TABLES is using the SQLITE in memory instead of the production Postgres.
* Add a breakpoint to the file: `src/modules/db_operations/main.py` in the line after the `dev run():` )
* Use the debugger to launch "Run DROP_AND_POPULATE_ALL_TABLES"

Step-through the db_operations code and use the interactive debugger to check values, load data from SQlite memory using the ORM via classes, etc. 



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
    * Update `version` in the file `src/modules/db_operations/module.env`. 

3. Move to the module folder and configure the module for deployment:
    ```bash
    cd src/modules/db_operations
    make configure
    ```
    * The module root folder should now contain a *.env* file
    * The module root folder SHOULD NOT contain a *venv* folder

4. Publish the module to GCR:
    ```bash
    make publish
    ```
    * When the command completes, check the [GCR](https://console.cloud.google.com/gcr/images/caendr/global/caendr-db-operations?authuser=1&project=caendr) and confirm your image with the proper version tag is appearing

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
    terraform plan -target module.db_operations -out tf_plan && terraform apply tf_plan
    ``` -->
