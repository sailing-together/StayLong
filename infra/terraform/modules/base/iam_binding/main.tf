resource "google_project_iam_member" "project" {
  for_each = {
    for binding in var.project_bindings : "${binding.role}:${binding.member}" => binding
  }

  project = var.project_id
  role    = each.value.role
  member  = each.value.member
}

resource "google_service_account_iam_member" "service_account" {
  for_each = {
    for index, binding in var.service_account_bindings : index => binding
  }

  service_account_id = each.value.service_account_id
  role               = each.value.role
  member             = each.value.member

  dynamic "condition" {
    for_each = each.value.condition == null ? [] : [each.value.condition]
    content {
      title       = condition.value.title
      description = condition.value.description
      expression  = condition.value.expression
    }
  }
}
