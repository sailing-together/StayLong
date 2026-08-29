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

resource "google_compute_global_address" "public" {
  project = local.config.project_id
  name    = "staylong-public-edge-ip"
}

resource "google_compute_region_network_endpoint_group" "cloud_run" {
  project               = local.config.project_id
  region                = local.config.region
  name                  = "staylong-public-edge-neg"
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = local.config.cloud_run_service_name
  }
}

resource "google_compute_backend_service" "public" {
  project               = local.config.project_id
  name                  = "staylong-public-edge-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  timeout_sec           = 30

  backend {
    group = google_compute_region_network_endpoint_group.cloud_run.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_managed_ssl_certificate" "public" {
  project = local.config.project_id
  name    = "staylong-public-edge-cert"

  managed {
    domains = [local.config.public_domain, local.config.www_public_domain]
  }
}

resource "google_compute_url_map" "https" {
  project         = local.config.project_id
  name            = "staylong-public-edge-https"
  default_service = google_compute_backend_service.public.id

  host_rule {
    hosts        = [local.config.www_public_domain]
    path_matcher = "www-redirect"
  }

  path_matcher {
    name = "www-redirect"

    default_url_redirect {
      host_redirect          = local.config.public_domain
      https_redirect         = true
      redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
      strip_query            = false
    }
  }
}

resource "google_compute_url_map" "http_redirect" {
  project = local.config.project_id
  name    = "staylong-public-edge-http"

  default_url_redirect {
    host_redirect          = local.config.public_domain
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_https_proxy" "public" {
  project          = local.config.project_id
  name             = "staylong-public-edge-https"
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_managed_ssl_certificate.public.id]
}

resource "google_compute_target_http_proxy" "redirect" {
  project = local.config.project_id
  name    = "staylong-public-edge-http"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "https" {
  project               = local.config.project_id
  name                  = "staylong-public-edge-https"
  ip_address            = google_compute_global_address.public.id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.public.id
}

resource "google_compute_global_forwarding_rule" "http" {
  project               = local.config.project_id
  name                  = "staylong-public-edge-http"
  ip_address            = google_compute_global_address.public.id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
}

resource "cloudflare_dns_record" "canonical" {
  zone_id = local.config.cloudflare_zone_id
  name    = local.config.public_domain
  type    = "A"
  content = google_compute_global_address.public.address
  proxied = false
  ttl     = 300
}

resource "cloudflare_dns_record" "www" {
  zone_id = local.config.cloudflare_zone_id
  name    = local.config.www_public_domain
  type    = "A"
  content = google_compute_global_address.public.address
  proxied = false
  ttl     = 300
}
