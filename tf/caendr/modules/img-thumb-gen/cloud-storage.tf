resource "google_storage_bucket" "source_bucket" {
  name = var.google_cloud_vars.source_bucket_name
  location = upper(var.google_cloud_vars.region)

  force_destroy = true 
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "photos_bucket" {
  name = var.bucket_photos_name
  location = upper(var.google_cloud_vars.region)
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.photos_bucket.name
  role   = "READER"
  entity = "allUsers"
}
