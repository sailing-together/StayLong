resource "google_project_service" "services" {
  for_each = toset(var.required_services)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "artifact_registry" {
  source = "../../base/artifact_registry"

  project_id    = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "Container images for StayLong"

  depends_on = [google_project_service.services]
}

module "runtime" {
  source = "../../base/service_account"

  project_id   = var.project_id
  account_id   = var.runtime_account_id
  display_name = "StayLong Cloud Run runtime"
  description  = "Least-privilege runtime identity for the StayLong service"
}
