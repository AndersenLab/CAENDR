
resource "google_cloud_tasks_queue" "db_op" {
  name = var.module_db_operations_vars.db_ops_task_queue_name
  location = "us-central1"

  rate_limits {
    max_concurrent_dispatches = 1
    max_dispatches_per_second = 1
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

