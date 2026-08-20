variable "project_config" { type = string }
variable "environment_config" { type = string }
variable "image_ref" { type = string }
variable "diagnostic_public_invoker" {
  type    = bool
  default = false
}
