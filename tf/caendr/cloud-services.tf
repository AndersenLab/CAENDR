resource "google_project_service" "cloud_resource_manager" {
  service = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service = "iam.googleapis.com"
  disable_on_destroy = false
  depends_on = [google_project_service.cloud_resource_manager]
}

resource "google_project_service" "container_registry" {
  service = "containerregistry.googleapis.com"
  disable_on_destroy = false
  depends_on = [google_project_service.cloud_resource_manager]
}

resource "google_project_service" "app_engine" {
  service = "appengine.googleapis.com"
  disable_on_destroy = false
  depends_on = [google_project_service.cloud_resource_manager]
}

resource "google_project_service" "app_engine_flex" {
  service = "appengineflex.googleapis.com"
  disable_on_destroy = false
  depends_on = [
    google_project_service.app_engine
  ]
}

resource "google_project_service" "sql_admin" {
  service = "sqladmin.googleapis.com"
  disable_on_destroy = false
  depends_on = [google_project_service.cloud_resource_manager]
}

resource "google_project_service" "secret_manager" {
  service = "secretmanager.googleapis.com"
  disable_on_destroy = false
  depends_on = [google_project_service.cloud_resource_manager]
}
