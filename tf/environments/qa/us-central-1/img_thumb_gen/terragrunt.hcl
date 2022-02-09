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
    source = "../../../../caendr/modules//img_thumb_gen"
}

inputs = {
    env = local.env
    ENVIRONMENT = local.env

    bucket_photos_name = get_env("MODULE_SITE_BUCKET_PHOTOS_NAME")
    image_source_path = get_env("MODULE_IMG_THUMB_GEN_SOURCE_PATH")

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
}