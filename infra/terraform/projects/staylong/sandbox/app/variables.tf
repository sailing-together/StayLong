variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "australia-southeast1"
}
variable "service_name" {
  type    = string
  default = "staylong"
}
variable "runtime_service_account" { type = string }
variable "image" { type = string }
