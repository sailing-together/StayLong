from pathlib import Path

COMPONENT_ROOT = Path("infra/terraform/components/public-edge")


def test_public_edge_component_owns_only_edge_resources() -> None:
    main = (COMPONENT_ROOT / "main.tf").read_text()
    versions = (COMPONENT_ROOT / "versions.tf").read_text()

    assert 'backend "gcs"' in main
    assert "cloudflare = {" in versions
    assert "google_compute_global_address" in main
    assert "google_compute_region_network_endpoint_group" in main
    assert 'network_endpoint_type = "SERVERLESS"' in main
    assert "google_compute_backend_service" in main
    assert 'load_balancing_scheme = "EXTERNAL_MANAGED"' in main
    assert "google_compute_managed_ssl_certificate" in main
    assert "google_compute_global_forwarding_rule" in main
    assert "cloudflare_dns_record" in main
    assert "proxied = false" in main
    assert "google_cloud_run_v2_service" not in main
    assert "CLOUDFLARE_API_TOKEN" not in main


def test_certificate_status_is_observed_by_the_lifecycle_workflow() -> None:
    outputs = (COMPONENT_ROOT / "outputs.tf").read_text()

    assert 'output "certificate_name"' in outputs
    assert 'output "certificate_status"' not in outputs
