output "workload_identity_provider" { value = module.bootstrap_identity.workload_identity_provider }
output "planner_service_account" { value = module.bootstrap_identity.planner_service_account }
output "operator_service_account" { value = module.bootstrap_identity.operator_service_account }
output "deployer_service_account" { value = module.bootstrap_identity.deployer_service_account }
