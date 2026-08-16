module "state_bucket" {
  source = "../../base/gcs_bucket"

  name                 = var.bucket_name
  project_id           = var.project_id
  location             = var.location
  force_destroy        = false
  object_admin_members = var.object_admin_members
}
