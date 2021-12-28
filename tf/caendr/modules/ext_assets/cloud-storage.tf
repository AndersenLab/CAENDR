resource "google_storage_bucket" "static_assets" {
  name = var.bucket_assets_name
  location = upper(var.google_cloud_vars.region)
  force_destroy = true 
  
  versioning {
    enabled = var.asset_versioning
  }

  cors {
    origin          = ["https://www.elegansvariation.org/", "http://localhost:8080/", "https://${var.google_cloud_vars.project_id}.uc.r.appspot.com/"]
    method          = ["GET", "HEAD", "DELETE", "PUT", "POST"]
    response_header = ["Content-Type", "Access-Control-Allow-Origin"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.static_assets.name
  role   = "READER"
  entity = "allUsers"
}
