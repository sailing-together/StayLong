variable "project_config" { type = string }
variable "environment_config" { type = string }

variable "image_ref" {
  description = "Container image selected for the same-service routing control."
  type        = string
}

variable "run_static_server" {
  description = "Override the image command with Python's minimal HTTP server."
  type        = bool
  default     = false
}

variable "run_uvicorn_h11" {
  description = "Override the image command with Uvicorn's pure-Python h11 parser."
  type        = bool
  default     = false
}
