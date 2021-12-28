src/modules/gene_browser_tracks
=============================================================================

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
