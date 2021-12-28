resource "google_storage_bucket" "source_bucket" {
  name = var.google_cloud_vars.source_bucket_name
  location = upper(var.google_cloud_vars.region)

  force_destroy = true 
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "photos_bucket" {
  name = var.bucket_photos_name
  location = upper(var.google_cloud_vars.region)
  
  cors {
    origin          = ["https://www.elegansvariation.org/", "http://localhost:8080/", "https://${var.google_cloud_vars.project_id}.uc.r.appspot.com/"]
    method          = ["GET", "HEAD", "DELETE", "PUT", "POST"]
    response_header = ["Content-Type", "Access-Control-Allow-Origin"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.photos_bucket.name
  role   = "READER"
  entity = "allUsers"
}

resource "google_storage_default_object_access_control" "public_rule" {
  bucket = google_storage_bucket.photos_bucket.name
  role   = "READER"
  entity = "allUsers"
}