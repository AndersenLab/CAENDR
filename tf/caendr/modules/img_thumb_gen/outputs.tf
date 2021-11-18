output "source_bucket" {
  value = google_storage_bucket.source_bucket.name
}

output "photos_bucket" {
  value = google_storage_bucket.photos_bucket.name
}
