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

# A disposable same-image control. The workflow always destroys it after the
# health check; it is never a StayLong deployment target.
module "service" {
  source = "../../modules/base/cloud_run_service"

  providers = {
    googlebeta = googlebeta
  }

  project_id            = local.config.project_id
  location              = local.config.region
  service_name          = "staylong-sydney-app-canary"
  service_account_email = "${local.config.runtime_account_id}@${local.config.project_id}.iam.gserviceaccount.com"
  image                 = var.canary_image
  enable_public_invoker = true
}
