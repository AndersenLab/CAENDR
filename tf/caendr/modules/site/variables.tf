variable "ENVIRONMENT" { }

variable "google_cloud_vars" { type = map(string) }
variable "module_site_vars" { type = map(string) }

# The 'sensitive' property is applied to the map values in the locals 
# definition to avoid the keys being considered sensitive as well
variable "cloud_secret_vars" { type = map(string) }
variable "cloud_sql_connection_uri" { type = string }
variable "api_pipeline_task_url" { type = string }