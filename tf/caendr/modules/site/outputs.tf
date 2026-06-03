output "site_bucket_public" {
  value = google_storage_bucket.site_bucket_public.name
}

output "site_bucket_private" {
  value = google_storage_bucket.site_bucket_private.name
}

output "site_url" {
  value = google_cloud_run_service.site.status
}