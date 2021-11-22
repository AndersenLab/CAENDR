src/modules/db_operations
=============================================================================

This directory contains the code to build the caendr-db-operations container which includes tools for performing long running database operations.

Database operations are scheduled in the Cloud Tasks Queue through the web admin portal, then executed by the api-pipeline-task module to prevent timeouts.

The operation to be performed is configured by defining the DATABASE_OPERATION environment variable and any arguments that may need to provided to that operation are defined using additional environment variables.

examples:
OP_NAME: ARG_NAME1, ARG_NAME2

export DATABASE_OPERATION=OP_NAME
export ARG_NAME1=argument value
export ARG_NAME2=another argument value
run.sh

ALT_OP:
export DATABASE_OPERATION=ALT_OP

DATABASE_OPERATIONs
---------------------------------------------------------------

DROP_ALL_TABLES:
DROP_AND_POPULATE_ALL_TABLES: WORMBASE_VERSION STRAIN_VARIANT_ANNOTATION_VERSION
MIGRATE_STAGE_DB:


