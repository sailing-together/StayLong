# Public edge operations

## Scope

This runbook covers the Terraform-managed public edge for `staylonghome.com`.
The public-edge component owns the global load balancer, serverless NEG,
certificate, and DNS records. It does not own the Cloud Run service or the
domain registration.

## Before the first provision

1. Confirm the non-secret domain and Cloudflare Zone ID are present in
   `staylong-public-sandbox.json`.
2. Apply the `bootstrap/identity` component through the documented
   human-authorised bootstrap path so the Terraform operator receives the
   public-edge IAM roles.
3. Wait for IAM propagation before running the protected public-domain
   workflow. Google Cloud IAM changes can take several minutes to become
   effective.
4. Confirm Cloudflare DNS records remain DNS-only while Google-managed TLS is
   provisioning.

## Rollback boundary

During Phase A, the existing Cloud Run `.run.app` URL remains available. If
the branded domain or certificate is unhealthy, stop before any ingress change
and investigate the public-edge component. The protected destroy operation may
remove only Terraform-managed edge resources; it never deletes the registered
domain.
