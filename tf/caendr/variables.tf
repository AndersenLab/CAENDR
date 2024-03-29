variable "ENVIRONMENT" { }


# Google Cloud Project Variables
variable "GOOGLE_CLOUD_PROJECT_ID" { }
variable "GOOGLE_CLOUD_PROJECT_NUMBER" { }
variable "GOOGLE_CLOUD_APP_LOCATION" { }
variable "GOOGLE_CLOUD_REGION" { }
variable "GOOGLE_CLOUD_SOURCE_BUCKET_NAME" { }
variable "TERRAFORM_SERVICE_ACCOUNT_FILENAME" { }
variable "GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME" { }
variable "GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME" { }
variable "GOOGLE_STORAGE_SERVICE_ACCOUNT_NAME" { }

variable "GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME" {}


# API Pipeline Task Variables
variable "MODULE_API_PIPELINE_TASK_CONTAINER_NAME" { }
variable "MODULE_API_PIPELINE_TASK_CONTAINER_VERSION" { }
variable "MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME" { }
variable "MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME" { }
variable "MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME" { }
variable "MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME" { }
variable "MODULE_API_PIPELINE_TASK_PUB_SUB_SUBSCRIPTION_NAME" { }
variable "MODULE_API_PIPELINE_TASK_CLOUDRUN_MIN_SCALE" { }
variable "MODULE_API_PIPELINE_TASK_CLOUDRUN_MAX_SCALE" { }


# Site Module Variables
variable "MODULE_SITE_CONTAINER_NAME" { type = string }
variable "MODULE_SITE_CLOUDRUN_SA_NAME" { type = string }
variable "MODULE_SITE_CONTAINER_VERSION" { type = string}
variable "MODULE_SITE_SERVING_STATUS" { type = bool }
variable "MODULE_SITE_BUCKET_ASSETS_NAME" { type = string }
variable "MODULE_SITE_BUCKET_PHOTOS_NAME" { type = string }
variable "MODULE_SITE_BUCKET_PUBLIC_NAME" { type = string }
variable "MODULE_SITE_BUCKET_PRIVATE_NAME" { type = string }
variable "NEMASCAN_TASK_QUEUE_NAME" { type = string }
variable "INDEL_PRIMER_TASK_QUEUE_NAME" { type = string }
variable "HERITABILITY_TASK_QUEUE_NAME" { type = string } 
variable "MODULE_API_PIPELINE_TASK_URL_NAME" { type = string }

# Maintenance Module Variables
variable "MODULE_MAINTENANCE_CONTAINER_NAME" { type = string }
variable "MODULE_MAINTENANCE_CONTAINER_VERSION" { type = string }

# DB-Operations Module Variables
variable "MODULE_DB_OPERATIONS_CONTAINER_NAME" { type = string }
variable "MODULE_DB_OPERATIONS_CONTAINER_VERSION" { type = string }
variable "MODULE_DB_OPERATIONS_INSTANCE_NAME" { type = string }
variable "MODULE_DB_OPERATIONS_DB_NAME" { type = string }
variable "MODULE_DB_OPERATIONS_DB_STAGE_NAME" { type = string }
variable "MODULE_DB_OPERATIONS_BUCKET_NAME" { type = string}
variable "ETL_LOGS_BUCKET_NAME" { type = string}
variable "MODULE_DB_OPERATIONS_DB_USER_NAME" { type = string}
variable "MODULE_DB_OPERATIONS_TASK_QUEUE_NAME" { type = string }


# Img-thumb-gen variables
variable "MODULE_IMG_THUMB_GEN_SOURCE_PATH" { }


# Secret variables
variable "ANDERSEN_LAB_STRAIN_SHEET" { sensitive = true }
variable "ANDERSEN_LAB_ORDER_SHEET" { sensitive = true }
variable "CENDR_PUBLICATIONS_SHEET" { sensitive = true }
variable "ELEVATION_API_KEY" { sensitive = true }
variable "RECAPTCHA_PUBLIC_KEY" { sensitive = true }
variable "RECAPTCHA_PRIVATE_KEY" { sensitive = true }
variable "GOOGLE_CLIENT_ID" { sensitive = true }
variable "GOOGLE_CLIENT_SECRET" { sensitive = true }
variable "POSTGRES_DB_PASSWORD" { sensitive = true }
variable "SECRET_KEY" { sensitive = true }
variable "JWT_SECRET_KEY" { sensitive = true }
variable "PASSWORD_PEPPER" { sensitive = true }
variable "MAILGUN_API_KEY" { sensitive = true }
variable "CC_EMAILS" { sensitive = true }
variable "CAENDR_API_SITE_ACCESS_TOKEN" { sensitive = true }
variable "NO_REPLY_EMAIL" { sensitive = true }

