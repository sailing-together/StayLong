module "bootstrap_state" {
  source = "../../../../modules/foundations/bootstrap_state"

  project_id           = var.project_id
  location             = var.location
  bucket_name          = var.state_bucket_name
  object_admin_members = var.object_admin_members
}
