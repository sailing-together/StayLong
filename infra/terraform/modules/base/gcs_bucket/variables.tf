variable "name" { type = string }
variable "project_id" { type = string }
variable "location" { type = string }
variable "force_destroy" {
  type    = bool
  default = false
}
variable "object_admin_members" {
  type    = list(string)
  default = []
}
