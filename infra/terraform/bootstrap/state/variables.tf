variable "project_id" { type = string }
variable "location" {
  type    = string
  default = "australia-southeast1"
}
variable "state_bucket_name" { type = string }
variable "object_admin_members" {
  type    = list(string)
  default = []
}
