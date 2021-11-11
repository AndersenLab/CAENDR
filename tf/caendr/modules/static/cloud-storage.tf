locals {
  asset_path = abspath("${path.module}/../../static*")
  file_set = fileset(local.asset_path, "**")
}

resource "google_storage_bucket" "static_assets" {
  name = var.module_static_vars.bucket_assets_name
  location = upper(var.google_cloud_vars.region)
  force_destroy = true 
  uniform_bucket_level_access = true

  versioning {
    enabled = var.asset_versioning
  }

  /*cors {
    origin          = ["https://www.elegansvariation.org/", "http://localhost:8080/"]
    method          = ["GET", "HEAD", "DELETE", "PUT", "POST"]
    response_header = ["Content-Type", "Access-Control-Allow-Origin"]
    max_age_seconds = 3600
  }*/
}


resource "google_storage_bucket_object" "asset" {
  for_each = local.file_set

  name         = each.key
  content_type = each.value.content_type
  source  = each.value.source_path
  content = each.value.content
  
  bucket = google_storage_bucket.static_assets.name
}
