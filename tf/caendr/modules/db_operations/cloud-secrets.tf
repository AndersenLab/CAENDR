
// Stores the JSON private key for the Google CloudSQL Service Account in the Cloud Secret Store
resource "google_secret_manager_secret" "cloudsql_sa_private_key" {
  project = var.google_cloud_vars.project_id
  provider = google-beta
  secret_id = var.google_cloud_vars.google_cloudsql_sa_name
  replication { 
    user_managed {
      replicas {
        location = "us-east1"
      }
      replicas {
        location = "us-central1"
      }
      replicas {
        location = "us-west1"
      }
    }
  }
}

resource "google_secret_manager_secret_version" "cloudsql_sa_private_key" {
  secret = google_secret_manager_secret.cloudsql_sa_private_key.id
  secret_data = sensitive(google_service_account_key.cloudsql_sa.private_key)
}
