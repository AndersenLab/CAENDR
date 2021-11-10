output "site_bucket_public" {
  value = google_storage_bucket.site_bucket_public.name
}

output "site_bucket_private" {
  value = google_storage_bucket.site_bucket_private.name
}

output "source_bucket" {
  value = google_storage_bucket.source_bucket.name
}

output "db_connection_name" {
  value = google_sql_database_instance.postgres_instance.connection_name
}
