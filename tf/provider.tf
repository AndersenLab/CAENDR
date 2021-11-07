terraform {
  required_version = ">= 0.12"
}

provider "google" {
  project     = var.GOOGLE_CLOUD_PROJECT_ID
  region      = var.GOOGLE_CLOUD_REGION
  credentials = file(var.GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE)
}

provider "google-beta" {
  project = var.GOOGLE_CLOUD_PROJECT_ID
  region  = var.GOOGLE_CLOUD_REGION
  credentials = file(var.GOOGLE_CLOUD_SERVICE_ACCOUNT_FILE)
}