variable "ENVIRONMENT" { }


# Google Cloud Project Variables
variable "GOOGLE_CLOUD_PROJECT_ID" { }
variable "GOOGLE_CLOUD_PROJECT_NUMBER" { }
variable "GOOGLE_CLOUD_APP_LOCATION" { }
variable "GOOGLE_CLOUD_REGION" { }
variable "GOOGLE_CLOUD_SOURCE_BUCKET_NAME" { }
variable "GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE" { }


# Site Module Variables
variable "MODULE_SITE_CONTAINER_NAME" { }
variable "MODULE_SITE_CONTAINER_VERSION" { }
variable "MODULE_SITE_SERVING_STATUS" { type = bool }
variable "MODULE_SITE_BUCKET_PUBLIC_NAME" { }
variable "MODULE_SITE_BUCKET_PRIVATE_NAME" { }
variable "MODULE_SITE_POSTGRES_INSTANCE_NAME" { }
variable "MODULE_SITE_POSTGRES_DB_NAME" { }
variable "MODULE_SITE_POSTGRES_DB_STAGE_NAME" { }


# Secret variables
variable "ANDERSEN_LAB_STRAIN_SHEET" { sensitive = true }
variable "CENDR_PUBLICATIONS_SHEET" { sensitive = true }
variable "RECAPTCHA_PUBLIC_KEY" { sensitive = true }
variable "RECAPTCHA_PRIVATE_KEY" { sensitive = true }
variable "ELEVATION_API_KEY" { sensitive = true }
variable "JWT_SECRET_KEY" { sensitive = true }
variable "PASSWORD_SALT" { sensitive = true }
variable "GOOGLE_CLIENT_ID" { sensitive = true }
variable "GOOGLE_CLIENT_SECRET" { sensitive = true }
variable "POSTGRES_DB_PASSWORD" { sensitive = true }
