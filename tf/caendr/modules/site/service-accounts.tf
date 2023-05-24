resource "google_service_account" "sheets_sa" {
  account_id   = var.google_cloud_vars.google_sheets_sa_name
  display_name = "Google Sheets Service Account"
}

resource "google_service_account_key" "sheets_sa" {
  service_account_id = google_service_account.sheets_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

resource "google_service_account" "analytics_sa" {
  account_id   = var.google_cloud_vars.google_analytics_sa_name
  display_name = "Google Analytics Service Account"
}

resource "google_service_account_key" "analytics_sa" {
  service_account_id = google_service_account.analytics_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

resource "google_service_account" "storage_sa" {
  account_id   = var.google_cloud_vars.google_storage_sa_name
  display_name = "Google Storage Service Account"
}

resource "google_service_account_key" "storage_sa" {
  service_account_id = google_service_account.storage_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

resource "google_service_account" "site" {
  account_id   = var.module_site_vars.cloudrun_site_sa_name
  display_name = "Google Cloud Run Service Account for the Site"
}

resource "google_service_account_key" "site" {
  service_account_id = google_service_account.site.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

locals {
  cloudrun_site_sa_roles = toset( [
    "roles/secretmanager.viewer",
    "roles/secretmanager.secretAccessor",
    "roles/storage.admin",
    "roles/cloudsql.client",
    "roles/datastore.user"
  ] )
}

resource "google_project_iam_member" "cloudrun_site_sa_roles_rg" {
  for_each = local.cloudrun_site_sa_roles

  project = var.google_cloud_vars.project_id
  member = "serviceAccount:${google_service_account.site.email}"
  role = each.key
}