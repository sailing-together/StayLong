variable "project_id" { type = string }
variable "location" { type = string }
variable "service_name" { type = string }
variable "service_account_email" { type = string }
variable "image" { type = string }
variable "invoker_members" {
  type    = set(string)
  default = []
}
variable "deletion_protection" {
  type    = bool
  default = false
}
