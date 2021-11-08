data "google_container_registry_image" "module_site" {
  name = var.module_site_vars.container_name
  tag = var.module_site_vars.container_version
}