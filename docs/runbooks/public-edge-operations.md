# Public edge operations

## Scope

This runbook covers the Terraform-managed public edge for `staylonghome.com`.
The public-edge component owns the global load balancer, serverless NEG,
certificate, and DNS records. It does not own the Cloud Run service or the
domain registration.

The branded endpoint is a temporary-data public demonstration: it permits
anonymous cookie sessions, never connects to a real provider, payment, Gmail,
or My Aged Care account, and its cases are routinely removed.

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

## Protected lifecycle workflow

Use **Actions → Control StayLong public domain → Run workflow** only after the
commit is reachable from `main`. The workflow uses GitHub OIDC and the
`sandbox` environment; `CLOUDFLARE_API_TOKEN` remains an environment secret
and is never written to Terraform variables, output, state, logs, or evidence.

- `provision` requires `PROVISION_PUBLIC_DOMAIN`. It creates only the
  Terraform-managed edge, waits up to 45 minutes for Google-managed TLS to be
  `ACTIVE`, then runs the public-domain smoke journey.
- `lockdown` requires `LOCKDOWN_PUBLIC_DOMAIN`. It first verifies the branded
  URL, and refuses unless the checked-in `public_edge_lockdown_enabled` switch
  is `true`. Do not use it during Phase A.
- `destroy` requires `DESTROY_PUBLIC_EDGE`. It destroys only the public-edge
  Terraform state; it never deletes the domain registration, Cloud Run service,
  or public-sandbox data store.

Every operation uploads a non-secret `public-edge-evidence-*` artifact with
the selected SHA, canonical URL, IP, certificate state, and smoke result.

## Rollback boundary

During Phase A, the existing Cloud Run `.run.app` URL remains available. If
the branded domain or certificate is unhealthy, stop before any ingress change
and investigate the public-edge component. The protected destroy operation may
remove only Terraform-managed edge resources; it never deletes the registered
domain.
