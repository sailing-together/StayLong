terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    googlebeta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = local.config.project_id
  region  = var.probe_region
}

provider "googlebeta" {
  project = local.config.project_id
  region  = var.probe_region
}
