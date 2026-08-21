locals {
  config_root = "${path.module}/../../projects/config"
  common      = jsondecode(file("${local.config_root}/common-environment.json"))
  environment = jsondecode(file("${local.config_root}/${var.environment_config}"))
  project     = jsondecode(file("${local.config_root}/${var.project_config}"))
  config = merge(local.common, local.environment, local.project, {
    labels = merge(local.common.labels, local.environment.labels, local.project.labels)
  })
  minimal_uvicorn_program = <<-PY
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()
    app.add_api_route("/healthz", lambda: {"status": "ok"})
    uvicorn.run(app, host="0.0.0.0", port=8080, loop="asyncio", http="h11")
  PY
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
      image = var.image_ref
      command = var.run_static_server || var.run_minimal_uvicorn ? ["python"] : (
        var.run_uvicorn_h11 ? ["uvicorn"] : []
      )
      args = var.run_static_server ? ["-m", "http.server", "8080"] : (
        var.run_minimal_uvicorn ? ["-c", local.minimal_uvicorn_program] : (
          var.run_uvicorn_h11 ? [
            "staylong.api.main:app", "--host", "0.0.0.0", "--port", "8080",
            "--http", "h11", "--loop", "asyncio"
          ] : []
        )
      )

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

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
    tag     = "probe"
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = local.config.project_id
  location = local.config.region
  name     = google_cloud_run_v2_service.control.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
