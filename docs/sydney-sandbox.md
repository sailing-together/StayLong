# Sydney sandbox recovery environment

The Melbourne Cloud Run endpoint returned gateway-level `404` responses even
after service replacement and a temporary public-invoker diagnostic. A
disposable public probe in `australia-southeast1` returned `200`, so StayLong
uses this independent Sydney sandbox while the Melbourne routing issue remains
open.

## Isolation

- `sydney-platform` owns only the `staylong-sydney` Artifact Registry
  repository in Sydney.
- `sydney-app` owns the private `staylong-sydney` Cloud Run service in Sydney.
- Both reuse the existing least-privilege runtime and deployer service
  accounts; they do not move or delete Melbourne resources.
- Terraform state is separate under `staylong/sydney-sandbox/`.

## Clean v2 rollout

The historical `staylong-sydney` service is retained as diagnostic evidence.
The clean replacement is deliberately named `staylong-sydney-v2`; it is created
once with the application image and a Secret Manager reference in its initial
revision, rather than creating a placeholder revision and mutating it later.

Before the v2 application root is applied, run the Terraform lifecycle workflow
with `environment=sydney-sandbox`, `component=sydney-v2-foundation` and a
reviewed `plan`/`apply`. This foundation enables Secret Manager, creates only
the `staylong-api-token` secret container, and grants:

- `staylong-runtime` access to read that one secret at runtime;
- `staylong-app-deployer` access only to add a secret version.

Terraform never receives the token value and therefore cannot record it in
state. The protected **Deploy Sydney v2 application** workflow adds the value
from the masked GitHub environment secret as a Secret Manager version, then
uses Terraform to create or update the v2 service with a secret reference. Do
not add token-like fields to the JSON configuration files: the configuration
validator rejects them by design.

## Delivery sequence

1. Run the Terraform lifecycle workflow with `environment=sydney-sandbox`,
   `component=sydney-platform`, and `operation=apply`.
2. Run it again with `component=sydney-app` and `operation=apply`.
3. Run **Deploy Sydney sandbox application revision** from `main`. It builds
   into the Sydney Artifact Registry repository and smoke-tests the private
   Sydney service with a WIF-minted ID token.

The existing Melbourne service remains available for evidence and should not
be treated as a deployment target until its Cloud Run routing issue is
resolved.

## Clean-project isolation

The rebuilt environment is now isolated in the GCP project `stay-long`. Its
configuration pair is `stay-long-sydney-v2.json` and
`stay-long-sydney-sandbox.json`. The state backend
`stay-long-terraform-state-864199179076` is a new, project-specific bucket;
it must be created by the standalone Terraform bootstrap before any remote
Terraform component or GitHub Actions workflow targets this environment.

This clean-project rollout is an isolation test for the earlier `staylong`
project's gateway-level Cloud Run `404`. It does not modify or destroy the
original project, state, services, or diagnostic evidence.
