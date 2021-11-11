locals {
  cloud_secret_vars_keys = toset([for k,v in var.cloud_secret_vars : k])
}

// Loops through all secrets set in the current environments secret.env
resource "google_secret_manager_secret" "app_engine_group" {
  for_each = local.cloud_secret_vars_keys

  project = var.google_cloud_vars.project_id
  provider = google-beta
  secret_id = each.key
  replication { automatic = true }
}

// Loops through all secrets set in the current environments secret.env
resource "google_secret_manager_secret_version" "app_engine_group" {
  for_each = google_secret_manager_secret.app_engine_group

  secret = each.value.name
  secret_data = lookup(var.cloud_secret_vars, each.value.secret_id)
}


// Stores the JSON private key for the Google Sheets Service Account in the Cloud Secret Store
resource "google_secret_manager_secret" "google_sheets_sa_private_key" {
  project = var.google_cloud_vars.project_id
  provider = google-beta
  secret_id = var.google_cloud_vars.google_sheets_sa_name
  replication { automatic = true }
}

resource "google_secret_manager_secret_version" "google_sheets_sa_private_key" {
  secret = google_secret_manager_secret.google_sheets_sa_private_key.id
  secret_data = google_service_account_key.sheets_sa.private_key
}


// Stores the JSON private key for the Google Analytics Service Account in the Cloud Secret Store
resource "google_secret_manager_secret" "google_analytics_sa_private_key" {
  project = var.google_cloud_vars.project_id
  provider = google-beta
  secret_id = var.google_cloud_vars.google_analytics_sa_name
  replication { automatic = true }
}

resource "google_secret_manager_secret_version" "google_analytics_sa_private_key" {
  secret = google_secret_manager_secret.google_analytics_sa_private_key.id
  secret_data = google_service_account_key.analytics_sa.private_key
}

