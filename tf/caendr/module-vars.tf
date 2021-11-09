locals {
  google_cloud_vars = tomap({
    "project_id" = "${var.GOOGLE_CLOUD_PROJECT_ID}",
    "project_number" = "${var.GOOGLE_CLOUD_PROJECT_NUMBER}",
    "region" = "${var.GOOGLE_CLOUD_REGION}",
    "app_location" = "${var.GOOGLE_CLOUD_APP_LOCATION}",
    "service_account_file" = "${var.GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE}",
    "source_bucket_name" = "${var.GOOGLE_CLOUD_SOURCE_BUCKET_NAME}"
  })

  module_site_vars = tomap({
    "container_name" = "${var.MODULE_SITE_CONTAINER_NAME}",
    "container_version" = "${var.MODULE_SITE_CONTAINER_VERSION}",
    "serving_status" = "${var.MODULE_SITE_SERVING_STATUS}",
    "bucket_public_name" = "${var.MODULE_SITE_BUCKET_PUBLIC_NAME}",
    "bucket_private_name" = "${var.MODULE_SITE_BUCKET_PRIVATE_NAME}",
    "postgres_instance_name" = "${var.MODULE_SITE_POSTGRES_INSTANCE_NAME}",
    "postgres_db_name" = "${var.MODULE_SITE_POSTGRES_DB_NAME}",
    "postgres_db_stage_name" = "${var.MODULE_SITE_POSTGRES_DB_STAGE_NAME}",
  })

  cloud_secret_vars = tomap({
    "ANDERSEN_LAB_STRAIN_SHEET" = sensitive("${var.ANDERSEN_LAB_STRAIN_SHEET}"), 
    "CENDR_PUBLICATIONS_SHEET" = sensitive("${var.CENDR_PUBLICATIONS_SHEET}"), 
    "RECAPTCHA_PUBLIC_KEY" = sensitive("${var.RECAPTCHA_PUBLIC_KEY}"), 
    "RECAPTCHA_PRIVATE_KEY" = sensitive("${var.RECAPTCHA_PRIVATE_KEY}"), 
    "ELEVATION_API_KEY" = sensitive("${var.ELEVATION_API_KEY}"), 
    "JWT_SECRET_KEY" = sensitive("${var.JWT_SECRET_KEY}"), 
    "PASSWORD_SALT" = sensitive("${var.PASSWORD_SALT}"), 
    "POSTGRES_DB_PASSWORD" = sensitive("${var.POSTGRES_DB_PASSWORD}"), 
    "GOOGLE_CLIENT_ID" = sensitive("${var.GOOGLE_CLIENT_ID}"), 
    "GOOGLE_CLIENT_SECRET" = sensitive("${var.GOOGLE_CLIENT_SECRET}"), 
  })
}
