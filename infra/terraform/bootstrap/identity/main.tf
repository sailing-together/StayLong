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

resource "google_project_service" "cloud_resource_manager" {
  project            = local.config.project_id
  service            = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "managed_identity_apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
  ])

  project            = local.config.project_id
  service            = each.value
  disable_on_destroy = false
}

data "google_project" "current" {
  project_id = local.config.project_id
}

module "github_federation" {
  source = "../../modules/foundations/github_federation"

  project_id                     = local.config.project_id
  github_repository              = local.config.github_repository
  github_branch                  = local.config.github_branch
  state_bucket_name              = local.config.state_bucket_name
  cloudbuild_staging_bucket_name = local.config.cloudbuild_staging_bucket_name
  project_number                 = data.google_project.current.number

  depends_on = [
    google_project_service.cloud_resource_manager,
    google_project_service.managed_identity_apis,
  ]
}
