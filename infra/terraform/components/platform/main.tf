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

module "sandbox_platform" {
  source = "../../modules/foundations/sandbox_platform"

  project_id                      = local.config.project_id
  region                          = local.config.region
  artifact_registry_repository_id = local.config.artifact_registry_repository_id
  runtime_account_id              = local.config.runtime_account_id
  deployer_account_id             = local.config.deployer_account_id
  cloudbuild_staging_bucket_name  = local.config.cloudbuild_staging_bucket_name
}
