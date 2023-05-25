data "google_iam_policy" "cloudrun_noauth" {
  binding {
    role = "roles/run.invoker"
    members = ["allUsers"]
  }
}

resource "google_cloud_run_service" "site" {
  name     = var.module_site_vars.container_name
  location = var.google_cloud_vars.region

  autogenerate_revision_name = true


  template {
    spec {
      containers {
        image = data.google_container_registry_image.module_site.image_url

        resources {
          limits = {
            cpu = "2"
            memory = "2Gi"
          }
        }
      }
      
      service_account_name = google_service_account.site.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = 3,
        "autoscaling.knative.dev/minScale" = 1,
        "run.googleapis.com/cpu-throttling" = false,
        "run.googleapis.com/startup-cpu-boost" = true,
        "run.googleapis.com/cloudsql-instances" = var.cloud_sql_connection_uri
        "run.googleapis.com/client-name" = "terraform"
      }
    }
  }



  traffic {
    percent         = 100
    latest_revision = true
  }

  

  depends_on = [
  ]
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = var.google_cloud_vars.region
  project     = var.google_cloud_vars.project_id
  service     = google_cloud_run_service.site.name

  policy_data = data.google_iam_policy.cloudrun_noauth.policy_data
}
