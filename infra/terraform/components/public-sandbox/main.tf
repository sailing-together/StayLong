terraform {
  backend "gcs" {}
}

locals {
  config_root = "${path.module}/../../projects/config"
  common      = jsondecode(file("${local.config_root}/common-environment.json"))
  environment = jsondecode(file("${local.config_root}/${var.environment_config}"))
  project     = jsondecode(file("${local.config_root}/${var.project_config}"))
  config = merge(local.common, local.environment, local.project, {
    labels = merge(local.common.labels, local.environment.labels, local.project.labels)
  })
}

# --- Service accounts ---

module "sandbox_runtime" {
  source = "../../modules/base/service_account"

  project_id   = local.config.project_id
  account_id   = local.config.runtime_account_id
  display_name = "StayLong public sandbox runtime"
  description  = "Least-privilege runtime identity for the StayLong public sandbox service"
}

module "sandbox_scheduler" {
  source = "../../modules/base/service_account"

  project_id   = local.config.project_id
  account_id   = local.config.scheduler_account_id
  display_name = "StayLong public sandbox cleanup scheduler"
  description  = "Dedicated identity for the scheduled public sandbox case-expiry job"
}

# --- Required APIs ---

resource "google_project_service" "secret_manager" {
  project            = local.config.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_scheduler" {
  project            = local.config.project_id
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firestore" {
  project            = local.config.project_id
  service            = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vertex_ai" {
  project            = local.config.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_firestore_database" "public_sandbox" {
  project                     = local.config.project_id
  name                        = "(default)"
  location_id                 = local.config.region
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"
  delete_protection_state     = "DELETE_PROTECTION_DISABLED"

  depends_on = [google_project_service.firestore]
}

# --- Session HMAC secret ---
# Signs the opaque HttpOnly session cookie; never the private API token.

module "session_secret" {
  source = "../../modules/base/secret_manager_secret"

  project_id = local.config.project_id
  secret_id  = "staylong-public-session-secret"
  labels     = local.config.labels
  accessor_members = [
    "serviceAccount:${module.sandbox_runtime.email}",
  ]

  depends_on = [google_project_service.secret_manager, module.sandbox_runtime]
}

# --- Minimal IAM for sandbox runtime ---

resource "google_project_iam_member" "sandbox_runtime_firestore" {
  project = local.config.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${module.sandbox_runtime.email}"
}

resource "google_project_iam_member" "sandbox_runtime_vertex" {
  project = local.config.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${module.sandbox_runtime.email}"
}

resource "google_project_iam_member" "sandbox_runtime_logging" {
  project = local.config.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${module.sandbox_runtime.email}"
}

# --- Cloud Run public sandbox service ---

resource "google_cloud_run_v2_service" "sandbox" {
  project  = local.config.project_id
  name     = "staylong-public-sandbox"
  location = local.config.region
  ingress = (
    local.config.public_edge_lockdown_enabled ?
    "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" : "INGRESS_TRAFFIC_ALL"
  )
  # `default_uri_disabled` is not exposed by the pinned Google provider. In
  # lockdown mode, INTERNAL_LOAD_BALANCER ingress prevents external bypass of
  # the generated .run.app address even while the API still reports that URL.
  deletion_protection = false

  template {
    service_account = module.sandbox_runtime.email

    scaling {
      # Keep one warm instance during the hackathon/demo window so the first
      # plan request does not pay the Cloud Run cold-start penalty. Revert to
      # 0 after the credits window to return to scale-to-zero billing.
      min_instance_count = 1
      max_instance_count = 3
    }

    containers {
      image = var.image_ref

      ports {
        container_port = 8080
      }

      env {
        name  = "STAYLONG_PUBLIC_SANDBOX"
        value = "true"
      }

      env {
        name  = "STAYLONG_GEMMA_ENABLED"
        value = "true"
      }

      # The public sandbox project does not have access to the Gemma publisher
      # model, so use an available Vertex model for the same privacy contract.
      env {
        name  = "STAYLONG_PRIVACY_MODEL"
        value = "gemini-2.5-flash"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = local.config.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }

      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }

      env {
        name  = "STAYLONG_GOOGLE_ACTIONS_MODE"
        value = "sandbox"
      }

      env {
        name = "STAYLONG_PUBLIC_SESSION_SECRET"
        value_source {
          secret_key_ref {
            secret  = module.session_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_firestore_database.public_sandbox,
    google_project_service.vertex_ai,
    module.sandbox_runtime,
    module.session_secret,
  ]
}

# Public invoker — anonymous browser access; private routes remain bearer-protected.
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = local.config.project_id
  location = local.config.region
  name     = google_cloud_run_v2_service.sandbox.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Scheduler invokes the cleanup endpoint with an OIDC token; anonymous calls are rejected.
resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  project  = local.config.project_id
  location = local.config.region
  name     = google_cloud_run_v2_service.sandbox.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${module.sandbox_scheduler.email}"
}

# --- Hourly cleanup job ---

resource "google_cloud_scheduler_job" "cleanup" {
  project   = local.config.project_id
  region    = local.config.region
  name      = "staylong-public-sandbox-cleanup"
  schedule  = "0 * * * *"
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.sandbox.uri}/internal/public-sandbox/cleanup"

    oidc_token {
      service_account_email = module.sandbox_scheduler.email
      audience              = google_cloud_run_v2_service.sandbox.uri
    }
  }

  depends_on = [google_project_service.cloud_scheduler]
}
