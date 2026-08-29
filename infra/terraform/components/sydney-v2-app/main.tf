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
  calendar_oauth_enabled = alltrue([
    var.calendar_oauth_client_id != "",
    var.calendar_oauth_redirect_uri != "",
    var.calendar_oauth_client_secret_id != "",
  ])
}

# Refresh tokens are stored in a Secret Manager secret named from a one-way
# hash of the private user identity. The runtime must create that secret only
# after the user completes OAuth, so these are the four API permissions it
# needs. Deliberately omit list, delete, IAM-policy, and admin permissions.
resource "google_project_iam_custom_role" "calendar_oauth_tokens" {
  count = local.calendar_oauth_enabled ? 1 : 0

  project     = local.config.project_id
  role_id     = "staylongCalendarOAuthTokens"
  title       = "StayLong Calendar OAuth token store"
  description = "Create, add, read, and access hashed private Calendar OAuth token secrets."
  permissions = [
    "secretmanager.secrets.create",
    "secretmanager.secrets.get",
    "secretmanager.versions.add",
    "secretmanager.versions.access",
  ]
}

resource "google_project_iam_member" "calendar_oauth_tokens" {
  count = local.calendar_oauth_enabled ? 1 : 0

  project = local.config.project_id
  role    = google_project_iam_custom_role.calendar_oauth_tokens[0].name
  member  = "serviceAccount:${local.config.runtime_account_id}@${local.config.project_id}.iam.gserviceaccount.com"
}

module "service" {
  source = "../../modules/base/cloud_run_service"

  providers = {
    googlebeta = googlebeta
  }

  project_id            = local.config.project_id
  location              = local.config.region
  service_name          = local.config.cloud_run_service_name
  service_account_email = "${local.config.runtime_account_id}@${local.config.project_id}.iam.gserviceaccount.com"
  image                 = var.image_ref
  enable_public_invoker = var.diagnostic_public_invoker
  environment_variables = merge({
    GOOGLE_CLOUD_PROJECT      = local.config.project_id
    GOOGLE_CLOUD_LOCATION     = "global"
    GOOGLE_GENAI_USE_VERTEXAI = "true"
    }, local.calendar_oauth_enabled ? {
    STAYLONG_GOOGLE_ACTIONS_MODE       = "oauth"
    STAYLONG_GOOGLE_OAUTH_CLIENT_ID    = var.calendar_oauth_client_id
    STAYLONG_GOOGLE_OAUTH_REDIRECT_URI = var.calendar_oauth_redirect_uri
  } : {})
  invoker_members = [
    "serviceAccount:${local.config.deployer_account_id}@${local.config.project_id}.iam.gserviceaccount.com",
  ]
  secret_environment_variables = merge({
    STAYLONG_API_TOKEN = {
      secret_id = "staylong-api-token"
      version   = "latest"
    }
    }, var.calendar_oauth_client_secret_id != "" ? {
    STAYLONG_GOOGLE_OAUTH_CLIENT_SECRET = {
      secret_id = var.calendar_oauth_client_secret_id
      version   = "latest"
    }
  } : {})
}
