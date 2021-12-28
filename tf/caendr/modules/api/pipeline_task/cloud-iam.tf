locals {
  api_pipeline_task_sa_roles = toset( [
    "roles/compute.serviceAgent",
    "roles/datastore.owner",
    "roles/lifesciences.workflowsRunner",
    "roles/storage.objectAdmin",
    "roles/secretmanager.viewer",
    "roles/secretmanager.secretAccessor",
    "roles/iam.serviceAccountUser",
    "roles/serviceusage.serviceUsageConsumer",
    "roles/pubsub.admin",
    "roles/cloudsql.admin"
  ] )
}


resource "google_project_iam_member" "api_pipeline_task_sa_roles_rg" {
  for_each = local.api_pipeline_task_sa_roles

  project = var.google_cloud_vars.project_id
  member = "serviceAccount:${google_service_account.api_pipeline_task.email}"
  role = each.key
}



