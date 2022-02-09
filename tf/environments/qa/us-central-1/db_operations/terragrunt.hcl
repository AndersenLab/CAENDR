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
    source = "../../../../caendr/modules//db_operations"
}

inputs = {
    ENVIRONMENT = local.env

    module_db_operations_vars = tomap({
      "container_name" = get_env("MODULE_DB_OPERATIONS_CONTAINER_NAME"),
      "container_version" = get_env("MODULE_DB_OPERATIONS_CONTAINER_VERSION"),
      "postgres_instance_name" = get_env("MODULE_DB_OPERATIONS_INSTANCE_NAME"),
      "postgres_db_name" = get_env("MODULE_DB_OPERATIONS_DB_NAME"),
      "postgres_db_stage_name" = get_env("MODULE_DB_OPERATIONS_DB_STAGE_NAME"),
      "postgres_db_password" = get_env("POSTGRES_DB_PASSWORD"),
      "postgres_db_user_name" = get_env("MODULE_DB_OPERATIONS_DB_USER_NAME"),
      "bucket_db_name" = get_env("MODULE_DB_OPERATIONS_BUCKET_NAME"),
      "db_ops_task_queue_name" = get_env("MODULE_DB_OPERATIONS_TASK_QUEUE_NAME")
    })

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

    asset_versioning = true

    depends_on = [
      # null_resource.api_service_group_all
    ]
    
}