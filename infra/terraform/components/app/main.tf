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

module "service" {
  source = "../../modules/base/cloud_run_service"

  providers = {
    google = google-beta
  }

  project_id            = local.config.project_id
  location              = local.config.region
  service_name          = local.config.cloud_run_service_name
  service_account_email = "${local.config.runtime_account_id}@${local.config.project_id}.iam.gserviceaccount.com"
  image                 = local.config.initial_image
  invoker_members = [
    "serviceAccount:${local.config.deployer_account_id}@${local.config.project_id}.iam.gserviceaccount.com",
  ]
}
