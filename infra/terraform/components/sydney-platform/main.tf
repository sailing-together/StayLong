terraform {
  backend "gcs" {}
}

locals {
  config_root = "${path.module}/../../projects/config"
  common      = jsondecode(file("${local.config_root}/common-environment.json"))
  environment = jsondecode(file("${local.config_root}/${var.environment_config}"))
  project     = jsondecode(file("${local.config_root}/${var.project_config}"))
  config = merge(local.common, local.environment, local.project, {
    labels = merge(local.common.labels, local.environment.labels, local.project.labels)
  })
}

resource "google_project_service" "artifact_registry" {
  project            = local.config.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

module "repository" {
  source = "../../modules/base/artifact_registry"

  project_id    = local.config.project_id
  location      = local.config.region
  repository_id = local.config.artifact_registry_repository_id
  description   = "Container images for StayLong Sydney sandbox"

  depends_on = [google_project_service.artifact_registry]
}
