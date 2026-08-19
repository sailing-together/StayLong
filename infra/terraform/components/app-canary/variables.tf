variable "project_config" { type = string }
variable "environment_config" { type = string }

variable "canary_image" {
  type        = string
  description = "Immutable image currently deployed by the Sydney StayLong service."
}
