module "state_backend" {
  source = "../../modules/foundations/state_backend"

  project_id           = var.project_id
  location             = var.location
  bucket_name          = var.state_bucket_name
  object_admin_members = var.object_admin_members
}
