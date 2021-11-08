resource "google_storage_bucket" "source_bucket" {
  name = var.google_cloud_vars.source_bucket_name
  location = upper(var.google_cloud_vars.region)

  force_destroy = true 
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "site_bucket_public" {
    name = var.module_site_vars.bucket_public_name
    location = upper(var.google_cloud_vars.region)
}

resource "google_storage_bucket" "site_bucket_private" {
    name = var.module_site_vars.bucket_private_name
    location = upper(var.google_cloud_vars.region)
}
