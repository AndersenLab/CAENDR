variable "ENVIRONMENT" { }

variable "google_cloud_vars" { type = map(string) }
variable "module_static_vars" { type = map(string) }
variable "asset_versioning" { type = bool }
