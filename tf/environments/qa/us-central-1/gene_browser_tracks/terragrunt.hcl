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
    source = "../../../../caendr/modules//gene_browser_tracks"
}

inputs = {
    ENVIRONMENT = local.env

    module_gene_browser_tracks_vars = tomap({
        "container_name" = get_env("MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME"),
        "container_version" = get_env("MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION"),
        "task_queue_name" = get_env("MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME")
    })

    google_cloud_vars = tomap({
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

    
}