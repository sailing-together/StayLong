variable "project_id" { type = string }
variable "pool_id" { type = string }
variable "provider_id" {
  type    = string
  default = "github"
}
variable "display_name" { type = string }
variable "description" {
  type    = string
  default = null
}
variable "attribute_mapping" { type = map(string) }
variable "attribute_condition" { type = string }
