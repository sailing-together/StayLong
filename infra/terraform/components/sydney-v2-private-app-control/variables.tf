variable "project_config" { type = string }
variable "environment_config" { type = string }

variable "image_ref" {
  description = "Immutable image digest copied from the affected StayLong revision."
  type        = string

  validation {
    condition     = strcontains(var.image_ref, "@sha256:")
    error_message = "image_ref must be an immutable container image digest."
  }
}
