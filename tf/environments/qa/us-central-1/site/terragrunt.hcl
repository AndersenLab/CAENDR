locals {
  # Automatically load environment-level variables
  environment_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))

  # Extract out common variables for reuse
  env = local.environment_vars.locals.environment
  project = local.environment_vars.locals.project
  OU = local.environment_vars.locals.OU
}

# Include all settings from the root terragrunt.hcl file
include {
  path = find_in_parent_folders()
}

terraform {
    source = "../../../../caendr/modules//site"
}

dependency "db_operations" {
	config_path = "../db_operations"
}

dependency "api_pipeline_task" {
	config_path = "../api_pipeline_task"
}

inputs = {
    ENVIRONMENT = local.env

    google_cloud_vars = tomap({
        "project_id" = get_env("GOOGLE_CLOUD_PROJECT_ID"),
        "project_number" = get_env("GOOGLE_CLOUD_PROJECT_NUMBER"),
        "region" = get_env("GOOGLE_CLOUD_REGION"),
        "app_location" = get_env("GOOGLE_CLOUD_APP_LOCATION"),
        "terraform_sa_filename" = get_env("TERRAFORM_SERVICE_ACCOUNT_FILENAME"),
        "google_sheets_sa_name" = get_env("GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME"),
        "google_analytics_sa_name" = get_env("GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME"),
        "google_storage_sa_name" = get_env("GOOGLE_STORAGE_SERVICE_ACCOUNT_NAME"),
        "google_cloudsql_sa_name" = get_env("GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME"),
        "source_bucket_name" = get_env("GOOGLE_CLOUD_SOURCE_BUCKET_NAME")
    })

    module_site_vars = tomap({
	"container_name" = var.MODULE_SITE_CONTAINER_NAME,
	"container_version" = var.MODULE_SITE_CONTAINER_VERSION,
	"serving_status" = var.MODULE_SITE_SERVING_STATUS,
	"bucket_public_name" = var.MODULE_SITE_BUCKET_PUBLIC_NAME,
	"bucket_private_name" = var.MODULE_SITE_BUCKET_PRIVATE_NAME,
	"nemascan_task_queue_name" = var.NEMASCAN_TASK_QUEUE_NAME,
	"indel_primer_task_queue_name" = var.INDEL_PRIMER_TASK_QUEUE_NAME
	"api_pipeline_task_url_name" = var.MODULE_API_PIPELINE_TASK_URL_NAME
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
	"PASSWORD_PEPPER" = sensitive(var.PASSWORD_PEPPER), 
	"MAILGUN_API_KEY" = sensitive(var.MAILGUN_API_KEY)
	"CC_EMAILS" = sensitive(var.CC_EMAILS)
	})

  cloud_sql_connection_uri = dependency.db_operations.outputs.db_connection_uri
  api_pipeline_task_url = deependency.api_pipeline_task.outputs.url


}
