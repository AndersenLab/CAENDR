locals {
  service_group_1 = toset([
    "cloudresourcemanager.googleapis.com"
  ])

  service_group_2 = toset([
    "iam.googleapis.com", 
    "containerregistry.googleapis.com",
    "appengine.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "secretmanager.googleapis.com",
    "sheets.googleapis.com",
    "drive.googleapis.com",
    "analyticsreporting.googleapis.com",
    "cloudtasks.googleapis.com"
  ])
  
  service_group_3 = toset([
    "appengineflex.googleapis.com"
  ])
}

resource "google_project_service" "api_service_group_1" {
  for_each = local.service_group_1

  service = each.key
  disable_on_destroy = false
}

resource "google_project_service" "api_service_group_2" {
  for_each = local.service_group_2

  service = each.key
  disable_on_destroy = false
  depends_on = [ google_project_service.api_service_group_1 ]
}

resource "google_project_service" "api_service_group_3" {
  for_each = local.service_group_3

  service = each.key
  disable_on_destroy = false
  depends_on = [ google_project_service.api_service_group_2 ]
}

resource "null_resource" "api_service_group_all" {
  depends_on = [ google_project_service.api_service_group_3 ]
}
