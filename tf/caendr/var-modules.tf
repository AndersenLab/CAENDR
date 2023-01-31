locals {
  google_cloud_vars = tomap({
    "project_id" = var.GOOGLE_CLOUD_PROJECT_ID,
    "project_number" = var.GOOGLE_CLOUD_PROJECT_NUMBER,
    "region" = var.GOOGLE_CLOUD_REGION,
    "app_location" = var.GOOGLE_CLOUD_APP_LOCATION,
    "terraform_sa_filename" = var.TERRAFORM_SERVICE_ACCOUNT_FILENAME,
    "google_sheets_sa_name" = var.GOOGLE_SHEETS_SERVICE_ACCOUNT_NAME,
    "google_analytics_sa_name" = var.GOOGLE_ANALYTICS_SERVICE_ACCOUNT_NAME,
    "google_storage_sa_name" = var.GOOGLE_STORAGE_SERVICE_ACCOUNT_NAME,
    "google_cloudsql_sa_name" = var.GOOGLE_CLOUDSQL_SERVICE_ACCOUNT_NAME,
    "source_bucket_name" = var.GOOGLE_CLOUD_SOURCE_BUCKET_NAME
  })

  module_site_vars = tomap({
    "container_name" = var.MODULE_SITE_CONTAINER_NAME,
    "container_version" = var.MODULE_SITE_CONTAINER_VERSION,
    "serving_status" = var.MODULE_SITE_SERVING_STATUS,
    "bucket_public_name" = var.MODULE_SITE_BUCKET_PUBLIC_NAME,
    "bucket_private_name" = var.MODULE_SITE_BUCKET_PRIVATE_NAME,
    "nemascan_task_queue_name" = var.NEMASCAN_TASK_QUEUE_NAME,
    "indel_primer_task_queue_name" = var.INDEL_PRIMER_TASK_QUEUE_NAME,
    "heritability_task_queue_name" = var.HERITABILITY_TASK_QUEUE_NAME,
    "api_pipeline_task_url_name" = var.MODULE_API_PIPELINE_TASK_URL_NAME
  })

  module_db_operations_vars = tomap({
    "container_name" = var.MODULE_DB_OPERATIONS_CONTAINER_NAME,
    "container_version" = var.MODULE_DB_OPERATIONS_CONTAINER_VERSION,
    "postgres_instance_name" = var.MODULE_DB_OPERATIONS_INSTANCE_NAME,
    "postgres_db_name" = var.MODULE_DB_OPERATIONS_DB_NAME,
    "postgres_db_stage_name" = var.MODULE_DB_OPERATIONS_DB_STAGE_NAME,
    "postgres_db_password" = sensitive(var.POSTGRES_DB_PASSWORD),
    "postgres_db_user_name" = var.MODULE_DB_OPERATIONS_DB_USER_NAME,
    "bucket_db_name" = var.MODULE_DB_OPERATIONS_BUCKET_NAME,
    "bucket_etl_logs_name" = var.ETL_LOGS_BUCKET_NAME,
    "db_ops_task_queue_name" = var.MODULE_DB_OPERATIONS_TASK_QUEUE_NAME
  })

  module_api_pipeline_task_vars = tomap({
    "container_name" = var.MODULE_API_PIPELINE_TASK_CONTAINER_NAME,
    "container_version" = var.MODULE_API_PIPELINE_TASK_CONTAINER_VERSION,
    "work_bucket_name" = var.MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME,
    "pipeline_task_sa_name" = var.MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME,
    "pub_sub_topic_name" = var.MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME,
    "pub_sub_subscription_name" = var.MODULE_API_PIPELINE_TASK_PUB_SUB_SUBSCRIPTION_NAME
  })

  module_gene_browser_tracks_vars = tomap({
    "container_name" = var.MODULE_GENE_BROWSER_TRACKS_CONTAINER_NAME,
    "container_version" = var.MODULE_GENE_BROWSER_TRACKS_CONTAINER_VERSION,
    "task_queue_name" = var.MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME
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
}
