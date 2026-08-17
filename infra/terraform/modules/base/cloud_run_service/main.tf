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
  # delivery changes the image and injects the runtime API token. Keep those
  # deployment-owned fields out of the infrastructure reconciliation loop.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].containers[0].env,
    ]
  }

  deletion_protection = var.deletion_protection
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  for_each = var.invoker_members

  project  = var.project_id
  location = var.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = each.value
}
