variable "project_id" { type = string }
variable "location" { type = string }
variable "bucket_name" { type = string }
variable "object_admin_members" {
  type    = list(string)
  default = []
}
