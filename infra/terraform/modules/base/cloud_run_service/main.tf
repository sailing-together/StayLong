resource "google_cloud_run_v2_service" "this" {
  project  = var.project_id
  name     = var.service_name
  location = var.location

  template {
    service_account = var.service_account_email

    containers {
      image = var.image
    }
  }

  # Terraform owns the service and all runtime configuration. Application
  # delivery changes only this immutable image reference to publish a revision.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  deletion_protection = var.deletion_protection
}
