resource "google_storage_bucket" "db_bucket" {
  name = var.module_db_operations_vars.bucket_db_name
  location = upper(var.google_cloud_vars.region)
}
