output "workload_identity_provider" { value = module.workload_identity.provider_name }
output "planner_service_account" { value = module.planner.email }
output "operator_service_account" { value = module.operator.email }
output "deployer_service_account" { value = module.deployer.email }
