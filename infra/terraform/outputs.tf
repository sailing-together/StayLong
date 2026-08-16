output "artifact_registry_repository" {
  value = google_artifact_registry_repository.staylong.name
}

output "github_deployer_service_account" {
  value = google_service_account.github_deployer.email
}

output "github_terraform_planner_service_account" {
  value = google_service_account.github_terraform_planner.email
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
