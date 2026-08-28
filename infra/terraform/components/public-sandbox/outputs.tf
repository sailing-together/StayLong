output "public_url" {
  description = "Public URL; branded edge after explicit lockdown, otherwise the generated Cloud Run URL."
  value = (
    local.config.public_edge_lockdown_enabled ?
    "https://${local.config.public_domain}" : google_cloud_run_v2_service.sandbox.uri
  )
}

output "service_name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.sandbox.name
}

output "cleanup_scheduler_job" {
  description = "Cloud Scheduler job name for the public sandbox case-expiry job."
  value       = google_cloud_scheduler_job.cleanup.name
}
