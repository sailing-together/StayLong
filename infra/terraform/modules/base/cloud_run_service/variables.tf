variable "project_id" { type = string }
variable "location" { type = string }
variable "service_name" { type = string }
variable "service_account_email" { type = string }
variable "image" { type = string }
variable "secret_environment_variables" {
  type = map(object({
    secret_id = string
    version   = string
  }))
  default = {}
}
variable "invoker_members" {
  type    = set(string)
  default = []
}
variable "enable_public_invoker" {
  type    = bool
  default = false
}
variable "deletion_protection" {
  type    = bool
  default = false
}
