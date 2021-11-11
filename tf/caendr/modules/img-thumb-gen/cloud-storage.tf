resource "google_storage_bucket" "source_bucket" {
  name = var.google_cloud_vars.source_bucket_name
  location = upper(var.google_cloud_vars.region)

  force_destroy = true 
  uniform_bucket_level_access = true
}
