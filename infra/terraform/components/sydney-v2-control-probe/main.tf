locals {
  config_root = "${path.module}/../../projects/config"
  common      = jsondecode(file("${local.config_root}/common-environment.json"))
  environment = jsondecode(file("${local.config_root}/${var.environment_config}"))
  project     = jsondecode(file("${local.config_root}/${var.project_config}"))
  config = merge(local.common, local.environment, local.project, {
    labels = merge(local.common.labels, local.environment.labels, local.project.labels)
  })
}

resource "google_cloud_run_v2_service" "control" {
  project             = local.config.project_id
  name                = "staylong-sydney-v2-control-probe"
  location            = local.config.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = "${local.config.runtime_account_id}@${local.config.project_id}.iam.gserviceaccount.com"

    containers {
      image = "gcr.io/google-samples/hello-app:1.0"

      ports {
        container_port = 8080
      }

      env {
        name = "STAYLONG_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "staylong-api-token"
            version = "latest"
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = local.config.project_id
  location = local.config.region
  name     = google_cloud_run_v2_service.control.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
