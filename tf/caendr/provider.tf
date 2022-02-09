terraform {
  backend "gcs" { 
    bucket = ""
    prefix = ""
  }
  required_version = ">= 1.0.0, < 2.0.0"
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
  # credentials = file(var.TERRAFORM_SERVICE_ACCOUNT_FILENAME)
}

provider "google-beta" {
  project = var.GOOGLE_CLOUD_PROJECT_ID
  region  = var.GOOGLE_CLOUD_REGION
  # credentials = file(var.TERRAFORM_SERVICE_ACCOUNT_FILENAME)
}
