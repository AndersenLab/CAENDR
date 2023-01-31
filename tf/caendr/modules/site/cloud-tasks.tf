resource "google_cloud_tasks_queue" "heritability" {
  name = var.module_site_vars.heritability_task_queue_name
  location = "us-central1"

  rate_limits {
    max_concurrent_dispatches = 5
    max_dispatches_per_second = 1
  }

  retry_config {
    max_attempts = 2
    max_backoff = "60s"
    min_backoff = "10s"
    max_doublings = 2
  }

  stackdriver_logging_config {
    sampling_ratio = 0.9
  }
}


resource "google_cloud_tasks_queue" "indel_primer" {
  name = var.module_site_vars.indel_primer_task_queue_name
  location = "us-central1"


  rate_limits {
    max_concurrent_dispatches = 1
    max_dispatches_per_second = 1
  }

  retry_config {
    max_attempts = 2
    max_backoff = "60s"
    min_backoff = "10s"
    max_doublings = 2
  }

  stackdriver_logging_config {
    sampling_ratio = 0.9
  }
}


resource "google_cloud_tasks_queue" "nemascan" {
  name = var.module_site_vars.nemascan_task_queue_name
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

