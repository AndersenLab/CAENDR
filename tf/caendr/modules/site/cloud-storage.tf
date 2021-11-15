resource "google_storage_bucket" "site_bucket_public" {
    name = var.module_site_vars.bucket_public_name
    location = upper(var.google_cloud_vars.region)
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.site_bucket_public.name
  role   = "READER"
  entity = "allUsers"
}


resource "google_storage_bucket" "site_bucket_private" {
    name = var.module_site_vars.bucket_private_name
    location = upper(var.google_cloud_vars.region)
}
