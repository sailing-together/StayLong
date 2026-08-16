module "workload_identity" {
  source = "../../base/workload_identity"

  project_id   = var.project_id
  pool_id      = var.pool_id
  display_name = "StayLong GitHub Actions"
  description  = "OIDC trust boundary for the approved GitHub repository"
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}'"
}

module "planner" {
  source = "../../base/service_account"

  project_id   = var.project_id
  account_id   = var.planner_account_id
  display_name = "StayLong Terraform planner"
  description  = "Read-only Terraform plan identity for GitHub Actions"
}

module "operator" {
  source = "../../base/service_account"

  project_id   = var.project_id
  account_id   = var.operator_account_id
  display_name = "StayLong Terraform operator"
  description  = "Approved sandbox Terraform apply identity for GitHub Actions"
}

module "deployer" {
  source = "../../base/service_account"

  project_id   = var.project_id
  account_id   = var.deployer_account_id
  display_name = "StayLong application deployer"
  description  = "Cloud Run revision deployer for GitHub Actions"
}

module "bindings" {
  source = "../../base/iam_binding"

  project_id = var.project_id
  project_bindings = concat(
    [for role in var.planner_project_roles : {
      role   = role
      member = "serviceAccount:${module.planner.email}"
    }],
    [for role in var.operator_project_roles : {
      role   = role
      member = "serviceAccount:${module.operator.email}"
    }],
    [for role in var.deployer_project_roles : {
      role   = role
      member = "serviceAccount:${module.deployer.email}"
    }],
  )
  service_account_bindings = [
    {
      service_account_id = module.planner.name
      role               = "roles/iam.workloadIdentityUser"
      member             = "principalSet://iam.googleapis.com/${module.workload_identity.pool_name}/attribute.repository/${var.github_repository}"
    },
    {
      service_account_id = module.operator.name
      role               = "roles/iam.workloadIdentityUser"
      member             = "principalSet://iam.googleapis.com/${module.workload_identity.pool_name}/attribute.repository/${var.github_repository}"
      condition = {
        title       = "protected_sandbox_branch"
        description = "Apply operations must originate from the protected branch."
        expression  = "attribute.ref == 'refs/heads/${var.github_branch}'"
      }
    },
    {
      service_account_id = module.deployer.name
      role               = "roles/iam.workloadIdentityUser"
      member             = "principalSet://iam.googleapis.com/${module.workload_identity.pool_name}/attribute.repository/${var.github_repository}"
      condition = {
        title       = "protected_sandbox_branch"
        description = "Deployments must originate from the protected branch."
        expression  = "attribute.ref == 'refs/heads/${var.github_branch}'"
      }
    },
  ]
}
