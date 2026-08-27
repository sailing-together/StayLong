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
    googlebeta = googlebeta
  }

  project_id            = local.config.project_id
  location              = local.config.region
  service_name          = local.config.cloud_run_service_name
  service_account_email = "${local.config.runtime_account_id}@${local.config.project_id}.iam.gserviceaccount.com"
  image                 = var.image_ref
  enable_public_invoker = var.diagnostic_public_invoker
  environment_variables = {
    GOOGLE_CLOUD_PROJECT = local.config.project_id
  }
  invoker_members = [
    "serviceAccount:${local.config.deployer_account_id}@${local.config.project_id}.iam.gserviceaccount.com",
  ]
  secret_environment_variables = {
    STAYLONG_API_TOKEN = {
      secret_id = "staylong-api-token"
      version   = "latest"
    }
  }
}
