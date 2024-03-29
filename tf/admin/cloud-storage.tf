resource "google_storage_bucket" "terraform_state" {
  name          = var.GOOGLE_CLOUD_TF_STATE_BUCKET_NAME
  location      = var.GOOGLE_CLOUD_REGION
  storage_class = "REGIONAL"
  versioning {
    enabled = true
  }
}