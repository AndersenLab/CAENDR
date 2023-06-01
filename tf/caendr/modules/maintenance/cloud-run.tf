data "google_iam_policy" "cloudrun_noauth" {
  binding {
    role = "roles/run.invoker"
    members = ["allUsers"]
  }
}

data "local_file" "env_file" {
  filename = "${path.module}/../../../../env/${var.ENVIRONMENT}/global.env"
}

locals {
  # Read the .env file contents from the local_file data source
  envs = [for line in split("\n", data.local_file.env_file.content): {
    name  = split("=", line)[0]
    value = split("=", line)[1]
    } if length(split("=", line)) == 2 && length(regexall("^#", line)) == 0
  ]
}


resource "google_cloud_run_service" "maintenance" {
  name     = var.module_maintenance_vars.container_name
  location = var.google_cloud_vars.region

  autogenerate_revision_name = true


  template {
    spec {
      containers {
        image = data.google_container_registry_image.module_maintenance.image_url

        dynamic "env" {
          for_each = local.envs
          content {
            name = env.value["name"]
            value = env.value["value"]
          }
        }

        resources {
          limits = {
            cpu = "1"
            memory = "512Mi"
          }
        }
      }
      
      # service_account_name = google_service_account.site.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = 1,
        "autoscaling.knative.dev/minScale" = 1,
        "run.googleapis.com/cpu-throttling" = false,
        "run.googleapis.com/startup-cpu-boost" = true,
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
  service     = google_cloud_run_service.maintenance.name

  policy_data = data.google_iam_policy.cloudrun_noauth.policy_data
}
