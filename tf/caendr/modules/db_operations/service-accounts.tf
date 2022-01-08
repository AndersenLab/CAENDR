locals {
  cloudsql_sa_roles = toset( [
    "roles/secretmanager.viewer",
    "roles/secretmanager.secretAccessor",
    "roles/storage.admin"
  ] )
}


resource "google_service_account" "cloudsql_sa" {
  account_id   = var.google_cloud_vars.google_cloudsql_sa_name
  display_name = "Cloud SQL Service Account"
}


resource "google_service_account_key" "cloudsql_sa" {
  service_account_id = google_service_account.cloudsql_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}


resource "google_project_iam_member" "cloudsql_sa_roles_rg" {
  for_each = local.cloudsql_sa_roles

  project = var.google_cloud_vars.project_id
  member = "serviceAccount:${google_service_account.cloudsql_sa.email}"
  role = each.key
}