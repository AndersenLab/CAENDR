module "site" {
  source = "./modules/site"
  ENVIRONMENT = var.ENVIRONMENT

  google_cloud_vars = local.google_cloud_vars
  module_site_vars = local.module_site_vars
  secret_vars = local.secret_vars

  depends_on = [
    google_project_service.iam,
    google_project_service.container_registry,
    google_project_service.app_engine_flex,
    google_project_service.sql_admin,
    google_project_service.secret_manager
  ]
}
