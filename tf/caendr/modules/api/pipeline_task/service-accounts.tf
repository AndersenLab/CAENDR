# Additional IAM roles for the App Engine and App Engine Flex default service accounts
locals {
  api_pipeline_task_sa_roles = toset( [
    "roles/compute.serviceAgent",
    "roles/datastore.owner",
    "roles/lifesciences.workflowsRunner",
    "roles/storage.objectCreator",
    "roles/storage.objectViewer"
  ] )
}


resource "google_service_account" "api_pipeline_task" {
  account_id   = var.module_api_pipeline_task_vars.pipeline_task_sa_name
  display_name = "API Pipeline Task Service Account"
}


resource "google_project_iam_member" "api_pipeline_task_sa_roles_rg" {
  for_each = local.api_pipeline_task_sa_roles

  project = var.google_cloud_vars.project_id
  member = "serviceAccount:${google_service_account.api_pipeline_task.email}"
  role = each.key
}



