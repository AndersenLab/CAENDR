output "terraform_state_bucket_name" {
  value       = google_storage_bucket.terraform_state.name
}