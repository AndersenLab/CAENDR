# Site
## src/modules/site
-------------------------------------------------------------------
The site module is an App Engine Flex container which uses Gunicorn as the Python WSGI HTTP Server (Web Server Gateway Interface) and Flask as the web framework with Jinja as the HTML template engine.

The contents of the `ext_assets` directory are copied to cloud storage by terraform and made public to the web. To embed an external asset in an HTML template use the `ext_asset()` jinja macro with the objects relative path in the ext_assets directory.

The `templates` directory contains all of the jinja HTML templates which are processed and returned by the view blueprints

The `base` directory includes:

- `base/views` - blueprint objects which define the site's structure and server-side page logic
- `base/utils` - utility functions which are either re-used or are too large to include within a view function
- `base/static` - static site resources, accessible from the *.com/static/ path because they must be served from the same domain (and I haven't set up a load balancer yet)
- `base/forms` - Flask forms and validators

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
    * Update `version` in the file `src/modules/site/module.env`. 

3. Move to the site module folder and configure the site module for deployment:
    ```bash
    cd src/modules/site
    make configure
    ```
    * The site module root folder should now contain a *.env* file
    * The site module root folder SHOULD NOT contain a *venv* folder

4. Move to the img_thumb_gen module folder and configure the img_thumb_gen module for deployment:
    * NOTE: The site module is dependent on the img_thumb_gen module when deploying, you do not need to version this module when deploying the site, but you will want to prep it for deployment or the publish to GCR will fail
    ```bash
    # from the project root
    cd src/modules/img_thumb_gen
    make configure
    ```
    * The img_thumb_gen module root folder should now contain a *.env* file
    * The img_thumb_gen module root folder SHOULD NOT contain a *venv* folder

5. Move back to the site module folder and publish the module to GCR:
    ```bash
    # from the project root
    cd src/modules/site
    make publish
    ```
    * When the command completes, check the [GCR](https://console.cloud.google.com/gcr/images/caendr/global/caendr-site?authuser=1&project=caendr) and confirm your image with the proper version tag is appearing

6. Deploy in Terraform shell:
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
    terraform plan -target module.site -out tf_plan && terraform apply tf_plan
    ```
