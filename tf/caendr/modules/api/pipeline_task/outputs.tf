output "url" {
  value = google_cloud_run_service.api_pipeline_task.status[0].url
}
