output "canonical_url" {
  description = "Canonical public URL served by the public edge."
  value       = "https://${local.config.public_domain}"
}

output "edge_ip" {
  description = "Reserved global IPv4 address for the public edge."
  value       = google_compute_global_address.public.address
}

output "certificate_name" {
  description = "Google-managed certificate resource name."
  value       = google_compute_managed_ssl_certificate.public.name
}

output "cloud_run_service_name" {
  description = "Existing Cloud Run service served through the edge."
  value       = google_compute_region_network_endpoint_group.cloud_run.cloud_run[0].service
}
