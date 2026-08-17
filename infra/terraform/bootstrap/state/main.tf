locals {
  config_root = "${path.module}/../../projects/config"
  common      = jsondecode(file("${local.config_root}/common-environment.json"))
  environment = jsondecode(file("${local.config_root}/${var.environment_config}"))
  project     = jsondecode(file("${local.config_root}/${var.project_config}"))
  config = merge(local.common, local.environment, local.project, {
    labels = merge(local.common.labels, local.environment.labels, local.project.labels)
  })
}

module "state_backend" {
  source = "../../modules/foundations/state_backend"

  project_id  = local.config.project_id
  location    = local.config.region
  bucket_name = local.config.state_bucket_name
}

module "cloudbuild_staging" {
  source = "../../modules/base/gcs_bucket"

  name       = local.config.cloudbuild_staging_bucket_name
  project_id = local.config.project_id
  location   = local.config.region
}
