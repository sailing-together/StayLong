variable "project_id" { type = string }

variable "project_bindings" {
  type    = list(object({ role = string, member = string }))
  default = []
}

variable "service_account_bindings" {
  type = list(object({
    service_account_id = string
    role               = string
    member             = string
    condition = optional(object({
      title       = string
      description = string
      expression  = string
    }))
  }))
  default = []
}
