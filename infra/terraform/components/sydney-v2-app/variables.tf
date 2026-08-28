variable "project_config" { type = string }
variable "environment_config" { type = string }
variable "image_ref" { type = string }
variable "diagnostic_public_invoker" {
  type    = bool
  default = false
}

variable "calendar_oauth_client_id" {
  description = "Google OAuth client ID for the private Calendar integration."
  type        = string
  default     = ""
}

variable "calendar_oauth_redirect_uri" {
  description = "Exact HTTPS callback URI registered for the private Calendar integration."
  type        = string
  default     = ""
}

variable "calendar_oauth_client_secret_id" {
  description = "Existing Secret Manager secret containing the Google OAuth client secret."
  type        = string
  default     = ""
}
