variable "project_config" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*\\.json$", var.project_config))
    error_message = "project_config must be a simple JSON filename."
  }
}
variable "environment_config" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*\\.json$", var.environment_config))
    error_message = "environment_config must be a simple JSON filename."
  }
}
