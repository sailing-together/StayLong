variable "project_id" { type = string }
variable "region" { type = string }
variable "artifact_registry_repository_id" {
  type    = string
  default = "staylong"
}
variable "runtime_account_id" {
  type    = string
  default = "staylong-runtime"
}
variable "required_services" {
  type = list(string)
  default = [
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudtasks.googleapis.com",
    "firestore.googleapis.com",
    "iamcredentials.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "sts.googleapis.com",
  ]
}
