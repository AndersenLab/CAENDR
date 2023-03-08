data "google_iam_policy" "cloudrun_noauth" {
  binding {
    role = "roles/run.invoker"
    members = ["allUsers"]
  }
}

locals {
    env_vars = { for tuple in regexall("(.*)=(.*)", file("${path.module}/../../../../env/${var.ENVIRONMENT}/global.env")) : tuple[0] => tuple[1] }
}


resource "google_cloud_run_service" "site" {
    name = var.module_site_vars.container_name
    location = var.google_cloud_vars.region

    autogenerate_revision_name = true

    template {
        spec {
            containers {
                image = data.google_container_registry_image.module_site.image_url

                env {
                    name = "ENV"
                    value = "${var.ENVIRONMENT}"
                }

                dynamic env {
                    for_each = local.env_vars
                    content {
                        name = env.key
                        value = env.value
                    }
                }
            }

            # TODO: create a new account instead of using the default GAE service account
            service_account_name = "${var.google_cloud_vars.project_id}@appspot.gserviceaccount.com"
        }

        metadata {
            annotations = {
                # "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.postgres_instance.connection_name
                "run.googleapis.com/cloudsql-instances" = "${var.cloud_sql_connection_uri}"
            }
        }

    }

    traffic {
        percent = 100
        latest_revision = true
    }


}