output "public_url" {
  description = "Public HTTPS URL of the StayLong public sandbox service."
  value       = google_cloud_run_v2_service.sandbox.uri
}

output "service_name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.sandbox.name
}

output "cleanup_scheduler_job" {
  description = "Cloud Scheduler job name for the public sandbox case-expiry job."
  value       = google_cloud_scheduler_job.cleanup.name
}
