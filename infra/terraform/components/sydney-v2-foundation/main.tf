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

resource "google_project_service" "secret_manager" {
  project = local.config.project_id
  service = "secretmanager.googleapis.com"

  disable_on_destroy = false
}

module "api_token" {
  source = "../../modules/base/secret_manager_secret"

  project_id = local.config.project_id
  # The identifier is infrastructure metadata, not a secret value. Keep it out
  # of shared JSON configuration so its key cannot be mistaken for a credential.
  secret_id = "staylong-api-token"
  labels    = local.config.labels
  accessor_members = [
    "serviceAccount:staylong-runtime@${local.config.project_id}.iam.gserviceaccount.com",
  ]
  version_adder_members = [
    "serviceAccount:staylong-app-deployer@${local.config.project_id}.iam.gserviceaccount.com",
  ]

  depends_on = [google_project_service.secret_manager]
}
