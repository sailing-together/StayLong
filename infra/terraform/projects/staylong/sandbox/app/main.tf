terraform {
  backend "gcs" {}
}

module "service" {
  source = "../../../../modules/base/cloud_run_service"

  project_id            = var.project_id
  location              = var.region
  service_name          = var.service_name
  service_account_email = var.runtime_service_account
  image                 = var.image
}
