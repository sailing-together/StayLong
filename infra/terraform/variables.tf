variable "project_id" {
  description = "Google Cloud project ID used for StayLong."
  type        = string
}

variable "region" {
  description = "Google Cloud region for StayLong services."
  type        = string
  default     = "australia-southeast1"
}

variable "github_repository" {
  description = "GitHub repository allowed to federate through WIF."
  type        = string
  default     = "sailing-together/StayLong"
}

variable "github_branch" {
  description = "Git branch permitted to deploy."
  type        = string
  default     = "main"
}
