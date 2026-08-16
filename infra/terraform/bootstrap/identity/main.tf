terraform {
  backend "gcs" {}
}

module "github_federation" {
  source = "../../modules/foundations/github_federation"

  project_id        = var.project_id
  github_repository = var.github_repository
  github_branch     = var.github_branch
}
