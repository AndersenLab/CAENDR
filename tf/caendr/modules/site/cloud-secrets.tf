locals {
  cloud_secret_vars_keys = toset([for k,v in var.cloud_secret_vars : k])
}

resource "google_secret_manager_secret" "app_engine_group" {
  for_each = local.cloud_secret_vars_keys

  project = var.google_cloud_vars.project_id
  provider = google-beta
  secret_id = each.key
  replication { automatic = true }
}

resource "google_secret_manager_secret_version" "app_engine_group" {
  for_each = google_secret_manager_secret.app_engine_group

  secret = each.value.name
  secret_data = lookup(var.cloud_secret_vars, each.value.secret_id)
}
