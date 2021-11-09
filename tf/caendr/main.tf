
data "google_project" "project" { }

module "site" {
  source = "./modules/site"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_site_vars = local.module_site_vars
  cloud_secret_vars = local.cloud_secret_vars
  github_vars = local.github_vars

  depends_on = [
    null_resource.api_service_group_all
  ]
}
