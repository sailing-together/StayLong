resource "google_cloud_run_v2_service" "this" {
  project  = var.project_id
  name     = var.service_name
  location = var.location

  # Keep the managed run.app endpoint available for authenticated smoke tests
  # and future load-balancer routing; IAM still controls who may invoke it.
  default_uri_disabled = false

  template {
    service_account = var.service_account_email

    containers {
      image = var.image
    }
  }

  # Terraform owns the service resource and access policy. Application
  # delivery owns the complete revision template (image and runtime secrets),
  # so infrastructure reconciliation must not roll a revision back to the
  # placeholder image or remove deployment-managed environment variables.
  lifecycle {
    ignore_changes = [template, scaling]
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
