data "google_iam_policy" "cloudrun_noauth" {
  binding {
    role = "roles/run.invoker"
    members = ["allUsers"]
  }
}

resource "google_cloud_run_service" "api_pipeline_task" {
  name     = var.module_api_pipeline_task_vars.container_name
  location = var.google_cloud_vars.region

  autogenerate_revision_name = true


  template {
    spec {
      containers {
        image = data.google_container_registry_image.api_pipeline_task.image_url
      }
      
      service_account_name = google_service_account.api_pipeline_task.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  

  depends_on = [
    null_resource.build_container_api_pipeline_task,
    null_resource.publish_container_api_pipeline_task,
    time_sleep.wait_container_publish_api_pipeline_task
  ]
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = var.google_cloud_vars.region
  project     = var.google_cloud_vars.project_id
  service     = google_cloud_run_service.api_pipeline_task.name

  policy_data = data.google_iam_policy.cloudrun_noauth.policy_data
}
