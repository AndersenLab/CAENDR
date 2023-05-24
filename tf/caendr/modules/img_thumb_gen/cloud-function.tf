resource "google_cloudfunctions_function" "generate_thumbnails" {
  available_memory_mb = "256"
  entry_point         = "generate_thumbnails"

  event_trigger {
    event_type = "google.storage.object.finalize"

    failure_policy {
      retry = "true"
    }

    resource = "projects/${var.google_cloud_vars.project_id}/buckets/${google_storage_bucket.photos_bucket.name}"
  }

  source_archive_bucket = google_storage_bucket.source_bucket.name
  source_archive_object = google_storage_bucket_object.source_zip.name

  ingress_settings = "ALLOW_ALL"

  max_instances         = "0"
  name                  = "generate_thumbnails"
  project               = "${var.google_cloud_vars.project_id}"
  region                = "${var.google_cloud_vars.region}"
  runtime               = "python37"
  service_account_email = "${var.google_cloud_vars.project_id}@appspot.gserviceaccount.com"
  timeout               = "60"

  depends_on = [ 
    google_storage_bucket_object.source_zip,
    time_sleep.wait_30_seconds
  ]
}

resource "time_sleep" "wait_30_seconds" {
  create_duration = "15s"
}