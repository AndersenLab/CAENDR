resource "google_storage_bucket" "site_bucket_public" {
  name = var.module_site_vars.bucket_public_name
  location = upper(var.google_cloud_vars.region)
  
  cors {
    origin          = ["https://www.elegansvariation.org/", "http://localhost:8080/", "https://${var.google_cloud_vars.project_id}.uc.r.appspot.com/"]
    method          = ["GET", "HEAD", "DELETE", "PUT", "POST"]
    response_header = ["Content-Type", "Access-Control-Allow-Origin"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.site_bucket_public.name
  role   = "READER"
  entity = "allUsers"
}

resource "google_storage_default_object_access_control" "public_rule" {
  bucket = google_storage_bucket.site_bucket_public.name
  role   = "READER"
  entity = "allUsers"
}


resource "google_storage_bucket" "site_bucket_private" {
  name = var.module_site_vars.bucket_private_name
  location = upper(var.google_cloud_vars.region)
  cors {
    origin          = ["https://www.elegansvariation.org/", "http://localhost:8080/", "https://${var.google_cloud_vars.project_id}.uc.r.appspot.com/"]
    method          = ["GET", "HEAD", "DELETE", "PUT", "POST"]
    response_header = ["Content-Type", "Access-Control-Allow-Origin"]
    max_age_seconds = 3600
  }
}

# TODO: MAKE THIS ACTUALLY PRIVATE EVENTUALLY
resource "google_storage_bucket_access_control" "private_rule" {
  bucket = google_storage_bucket.site_bucket_private.name
  role   = "READER"
  entity = "allUsers"
}

resource "google_storage_default_object_access_control" "private_rule" {
  bucket = google_storage_bucket.site_bucket_private.name
  role   = "READER"
  entity = "allUsers"
}

