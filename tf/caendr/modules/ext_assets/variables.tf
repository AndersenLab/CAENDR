variable "ENVIRONMENT" { }

variable "google_cloud_vars" { type = map(string) }
variable "asset_versioning" { type = bool }
variable "bucket_assets_name" { type = string }
