#!/bin/bash

# Load .env file as environment variables
export $(cat .env | sed -e '/^\s*$/d' | sed -e '/^\#/d' | xargs)

# Cloud SQL Proxy is required to connect to Cloud SQL Instance
./cloud_sql_proxy -instances=$GOOGLE_CLOUD_PROJECT_ID:$GOOGLE_CLOUD_REGION:$MODULE_DB_OPERATIONS_INSTANCE_NAME -dir=/cloudsql &

# Run DATABASE_OPERATION
python main.py