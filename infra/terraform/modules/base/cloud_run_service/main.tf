resource "google_cloud_run_v2_service" "this" {
  provider = googlebeta

  project  = var.project_id
  name     = var.service_name
  location = var.location

  # Keep the generated run.app endpoints available for the sandbox demo and
  # make the routing choice explicit in Terraform state.
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
  provider = googlebeta

  for_each = var.invoker_members

  project  = var.project_id
  location = var.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = each.value

  # IAM policies are attached to the service resource. Recreate each binding
  # whenever a guarded service replacement is deliberately requested.
  lifecycle {
    replace_triggered_by = [google_cloud_run_v2_service.this]
  }
}

# This binding is only enabled by the guarded public-diagnostic workflow. It
# must never be enabled by regular app apply/deploy operations.
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  provider = googlebeta
  count    = var.enable_public_invoker ? 1 : 0

  project  = var.project_id
  location = var.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
