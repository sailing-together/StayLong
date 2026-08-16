terraform {
  backend "gcs" {}
}

module "bootstrap_identity" {
  source = "../../../../modules/foundations/bootstrap_identity"

  project_id        = var.project_id
  github_repository = var.github_repository
  github_branch     = var.github_branch
}
