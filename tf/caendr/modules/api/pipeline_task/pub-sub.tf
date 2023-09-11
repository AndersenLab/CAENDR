locals {
  status_route = "task/status"
}

resource "google_pubsub_topic" "pipeline_task" {
  message_storage_policy {
    allowed_persistence_regions = ["us-central1", 
                                  "us-central2", 
                                  "us-east1", 
                                  "us-east4", 
                                  "us-west1", 
                                  "us-west2", 
                                  "us-west3", 
                                  "us-west4"]
  }

  name    = var.module_api_pipeline_task_vars.pub_sub_topic_name
  project = var.google_cloud_vars.project_id
}


resource "google_pubsub_subscription" "pipeline_task" {
  ack_deadline_seconds    = "10"
  enable_message_ordering = "false"

  expiration_policy {
    ttl = "2678400s"
  }

  retry_policy {
    minimum_backoff = "60s"
    maximum_backoff = "300s"
  }

  message_retention_duration = "259200s"
  name                       = var.module_api_pipeline_task_vars.pub_sub_subscription_name
  project                    = var.google_cloud_vars.project_id

  push_config {
    push_endpoint = "${google_cloud_run_service.api_pipeline_task.status[0].url}/${local.status_route}"
  }

  retain_acked_messages = "false"
  topic                 = google_pubsub_topic.pipeline_task.name
  
  depends_on = [
    google_cloud_run_service.api_pipeline_task,
    google_pubsub_topic.pipeline_task,
  ]
}
