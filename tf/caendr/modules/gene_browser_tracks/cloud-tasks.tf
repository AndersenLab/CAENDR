
resource "google_cloud_tasks_queue" "gene_browser_tracks" {
  name = var.module_gene_browser_tracks_vars.task_queue_name
  location = "us-central1"

  rate_limits {
    max_concurrent_dispatches = 1
    max_dispatches_per_second = 0.001
  }

  retry_config {
    max_attempts = 1
    max_backoff = "3000s"
    min_backoff = "300s"
  }

  stackdriver_logging_config {
    sampling_ratio = 0.9
  }
}

