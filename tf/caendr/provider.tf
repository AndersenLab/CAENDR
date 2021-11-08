terraform {
  backend "gcs" { }
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
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
