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
    "attribute.repository_ref"   = "assertion.repository + \":\" + assertion.ref"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}'"
}

locals {
  protected_branch_principal = "principalSet://iam.googleapis.com/${module.workload_identity.pool_name}/attribute.repository_ref/${var.github_repository}:refs/heads/${var.github_branch}"
  terraform_state_members = {
    "planner"  = module.planner.email
    "operator" = module.operator.email
  }
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
      member             = local.protected_branch_principal
    },
    {
      service_account_id = module.deployer.name
      role               = "roles/iam.workloadIdentityUser"
      member             = local.protected_branch_principal
    },
  ]
}

resource "google_storage_bucket_iam_member" "terraform_state" {
  for_each = local.terraform_state_members

  bucket = var.state_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${each.value}"
}

locals {
  cloudbuild_staging_members = {
    deployer_creator = {
      role   = "roles/storage.objectCreator"
      member = "serviceAccount:${module.deployer.email}"
    }
    deployer_viewer = {
      role   = "roles/storage.objectViewer"
      member = "serviceAccount:${module.deployer.email}"
    }
    deployer_bucket_reader = {
      role   = "roles/storage.legacyBucketReader"
      member = "serviceAccount:${module.deployer.email}"
    }
    cloudbuild_creator = {
      role   = "roles/storage.objectCreator"
      member = "serviceAccount:service-${var.project_number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
    }
    cloudbuild_viewer = {
      role   = "roles/storage.objectViewer"
      member = "serviceAccount:service-${var.project_number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
    }
    cloudbuild_bucket_reader = {
      role   = "roles/storage.legacyBucketReader"
      member = "serviceAccount:service-${var.project_number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
    }
    compute_source_viewer = {
      role   = "roles/storage.objectViewer"
      member = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
    }
    compute_bucket_reader = {
      role   = "roles/storage.legacyBucketReader"
      member = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
    }
  }
}

resource "google_storage_bucket_iam_member" "cloudbuild_staging" {
  for_each = local.cloudbuild_staging_members

  bucket = var.cloudbuild_staging_bucket_name
  role   = each.value.role
  member = each.value.member
}
