
resource "google_secret_manager_secret" "api_pipeline_task_sa_private_key" {
  project = var.google_cloud_vars.project_id
  provider = google-beta
  secret_id = var.module_api_pipeline_task_vars.pipeline_task_sa_name
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

resource "google_secret_manager_secret_version" "api_pipeline_task_sa_private_key" {
  secret = google_secret_manager_secret.api_pipeline_task_sa_private_key.id
  secret_data = sensitive(google_service_account_key.api_pipeline_task.private_key)
}
