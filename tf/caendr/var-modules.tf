locals {
  google_cloud_vars = tomap({
    "project_id" = var.GOOGLE_CLOUD_PROJECT_ID,
    "project_number" = var.GOOGLE_CLOUD_PROJECT_NUMBER,
    "region" = var.GOOGLE_CLOUD_REGION,
    "app_location" = var.GOOGLE_CLOUD_APP_LOCATION,
    "terraform_sa_filename" = var.TERRAFORM_SERVICE_ACCOUNT_FILENAME,
    "google_sheets_sa_name" = var.GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME,
    "google_analytics_sa_name" = var.GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME,
    "google_cloudsql_sa_name" = var.GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME,
    "source_bucket_name" = var.GOOGLE_CLOUD_SOURCE_BUCKET_NAME
  })

  module_site_vars = tomap({
    "container_name" = var.MODULE_SITE_CONTAINER_NAME,
    "container_version" = var.MODULE_SITE_CONTAINER_VERSION,
    "serving_status" = var.MODULE_SITE_SERVING_STATUS,
    "bucket_public_name" = var.MODULE_SITE_BUCKET_PUBLIC_NAME,
    "bucket_private_name" = var.MODULE_SITE_BUCKET_PRIVATE_NAME,
  })

  module_db_operations_vars = tomap({
    "postgres_instance_name" = var.MODULE_DB_OPERATIONS_INSTANCE_NAME,
    "postgres_db_name" = var.MODULE_DB_OPERATIONS_DB_NAME,
    "postgres_db_stage_name" = var.MODULE_DB_OPERATIONS_DB_STAGE_NAME,
    "postgres_db_password" = sensitive(var.POSTGRES_DB_PASSWORD),
    "postgres_db_user_name" = var.MODULE_DB_OPERATIONS_DB_USER,
    "bucket_db_name" = var.MODULE_DB_OPERATIONS_BUCKET_NAME
  })

  cloud_secret_vars = tomap({
    "ANDERSEN_LAB_STRAIN_SHEET" = sensitive(var.ANDERSEN_LAB_STRAIN_SHEET), 
    "ANDERSEN_LAB_ORDER_SHEET" = sensitive(var.ANDERSEN_LAB_ORDER_SHEET), 
    "CENDR_PUBLICATIONS_SHEET" = sensitive(var.CENDR_PUBLICATIONS_SHEET), 
    "ELEVATION_API_KEY" = sensitive(var.ELEVATION_API_KEY), 
    "RECAPTCHA_PUBLIC_KEY" = sensitive(var.RECAPTCHA_PUBLIC_KEY), 
    "RECAPTCHA_PRIVATE_KEY" = sensitive(var.RECAPTCHA_PRIVATE_KEY), 
    "GOOGLE_CLIENT_ID" = sensitive(var.GOOGLE_CLIENT_ID), 
    "GOOGLE_CLIENT_SECRET" = sensitive(var.GOOGLE_CLIENT_SECRET), 
    "POSTGRES_DB_PASSWORD" = sensitive(var.POSTGRES_DB_PASSWORD), 
    "SECRET_KEY" = sensitive(var.SECRET_KEY),
    "JWT_SECRET_KEY" = sensitive(var.JWT_SECRET_KEY), 
    "PASSWORD_SALT" = sensitive(var.PASSWORD_SALT), 
    "MAILGUN_API_KEY" = sensitive(var.MAILGUN_API_KEY)
  })
}
