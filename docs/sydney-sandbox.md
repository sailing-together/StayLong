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
state. A later protected deployment workflow will write the value from the
masked GitHub environment secret and deploy the v2 service using the secret
reference. Do not add token-like fields to the JSON configuration files: the
configuration validator rejects them by design.

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
