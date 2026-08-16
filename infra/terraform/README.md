# Terraform

Terraform will provision the StayLong Google Cloud foundation and GitHub OIDC Workload Identity Federation configuration.

## Required variables

- `project_id`: target Google Cloud project ID
- `region`: Google Cloud region, for example `australia-southeast1`
- `github_repository`: `sailing-together/StayLong`
- `github_branch`: protected deployment branch, initially `main`

## Safety

Pull requests use a read-only Terraform planner identity. An approved manual apply runs only from the protected deployment branch and uses the deployer identity. Never add Google service-account JSON keys as repository secrets; deployment uses GitHub OIDC/WIF.

After the first apply, copy the Terraform outputs into the GitHub `production` environment variables:

- `GCP_WIF_PROVIDER`
- `GCP_TERRAFORM_SERVICE_ACCOUNT` (the planner output)
- `GCP_DEPLOY_SERVICE_ACCOUNT` (the deployer output)
- `GCP_RUNTIME_SERVICE_ACCOUNT` (the Cloud Run runtime identity, created in the next application delivery task)
- `GCP_PROJECT_ID` and `GCP_REGION`
