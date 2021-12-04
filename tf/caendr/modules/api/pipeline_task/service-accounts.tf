resource "google_service_account" "api_pipeline_task" {
  account_id   = var.module_api_pipeline_task_vars.pipeline_task_sa_name
  display_name = "API Pipeline Task Service Account"
}


resource "google_service_account_key" "api_pipeline_task" {
  service_account_id = google_service_account.api_pipeline_task.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

