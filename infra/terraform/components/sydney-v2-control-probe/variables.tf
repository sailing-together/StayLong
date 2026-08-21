variable "project_config" { type = string }
variable "environment_config" { type = string }

variable "image_ref" {
  description = "Container image selected for the same-service routing control."
  type        = string
}
