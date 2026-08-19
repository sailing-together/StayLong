variable "project_id" { type = string }
variable "github_repository" { type = string }
variable "github_branch" { type = string }
variable "state_bucket_name" { type = string }
variable "cloudbuild_staging_bucket_name" { type = string }
variable "project_number" { type = string }
variable "pool_id" {
  type    = string
  default = "staylong-github"
}
variable "planner_account_id" {
  type    = string
  default = "staylong-tf-planner"
}
variable "operator_account_id" {
  type    = string
  default = "staylong-tf-operator"
}
variable "deployer_account_id" {
  type    = string
  default = "staylong-app-deployer"
}
variable "planner_project_roles" {
  type    = list(string)
  default = ["roles/viewer"]
}
variable "operator_project_roles" {
  type = list(string)
  default = [
    "roles/artifactregistry.admin",
    "roles/cloudtasks.admin",
    "roles/datastore.owner",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/pubsub.admin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/serviceusage.serviceUsageAdmin",
  ]
}
variable "deployer_project_roles" {
  type = list(string)
  default = [
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.editor",
    "roles/iam.serviceAccountUser",
    "roles/run.admin",
    "roles/serviceusage.serviceUsageConsumer",
  ]
}
