output "artifact_registry_repository" { value = module.artifact_registry.name }
output "runtime_service_account" { value = module.runtime.email }
output "cloudbuild_staging_bucket" { value = module.cloudbuild_staging.name }
