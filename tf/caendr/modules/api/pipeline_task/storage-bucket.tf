resource "google_storage_bucket" "pipeline_work" {
  name = var.module_api_pipeline_task_vars.work_bucket_name
  location = upper(var.google_cloud_vars.region)
}

resource "google_storage_bucket" "pipeline_report" {
  name = var.module_api_pipeline_task_vars.pipeline_report_name
  location = upper(var.google_cloud_vars.region)
}
