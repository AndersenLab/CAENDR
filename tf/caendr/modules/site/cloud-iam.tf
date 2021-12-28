# Additional IAM roles for the App Engine and App Engine Flex default service accounts
locals {
  app_engine_sa_roles = toset( [
    "roles/secretmanager.viewer",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectViewer",
    "roles/datastore.user"
  ] )
}

resource "google_project_iam_member" "app_engine_sa_roles_rg" {
  for_each = local.app_engine_sa_roles

  project = var.google_cloud_vars.project_id
  member = "serviceAccount:${var.google_cloud_vars.project_id}@appspot.gserviceaccount.com"
  role = each.key
}

resource "google_project_iam_member" "app_engine_flex_sa_roles_rg" {
  for_each = local.app_engine_sa_roles

  project = var.google_cloud_vars.project_id
  member  = "serviceAccount:service-${var.google_cloud_vars.project_number}@gae-api-prod.google.com.iam.gserviceaccount.com"
  role = each.key
}

