terraform {
  backend "gcs" {}
}

module "sandbox_platform" {
  source = "../../../../modules/foundations/sandbox_platform"

  project_id = var.project_id
  region     = var.region
}
