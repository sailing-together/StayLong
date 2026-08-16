resource "google_project_service" "services" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "cloudtasks.googleapis.com",
    "pubsub.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "staylong" {
  location      = var.region
  repository_id = "staylong"
  description   = "Container images for StayLong"
  format        = "DOCKER"

  depends_on = [google_project_service.services]
}

resource "google_service_account" "runtime" {
  account_id   = "staylong-runtime"
  display_name = "StayLong Cloud Run runtime"
}

resource "google_service_account" "github_deployer" {
  account_id   = "staylong-github-deployer"
  display_name = "StayLong GitHub Actions deployer"
}

resource "google_service_account" "github_terraform_planner" {
  account_id   = "staylong-tf-planner"
  display_name = "StayLong GitHub Actions Terraform planner"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "staylong-github"
  display_name              = "StayLong GitHub Actions"
  description               = "OIDC trust boundary for the StayLong repository"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub Actions"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  # The provider accepts identity tokens only from this repository. The
  # individual service-account bindings below further limit deployment to main.
  attribute_condition = "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_wif" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"

  condition {
    title       = "main_branch_deployments_only"
    description = "Only the protected deployment branch can impersonate the deployer."
    expression  = "attribute.ref == 'refs/heads/${var.github_branch}'"
  }
}

resource "google_service_account_iam_member" "github_terraform_planner_wif" {
  service_account_id = google_service_account.github_terraform_planner.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_project_iam_member" "github_deployer_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.github_deployer.email}"
}

resource "google_project_iam_member" "github_terraform_planner_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.github_terraform_planner.email}"
}
