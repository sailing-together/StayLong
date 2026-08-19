variable "project_id" { type = string }
variable "secret_id" { type = string }
variable "labels" {
  type    = map(string)
  default = {}
}
variable "accessor_members" {
  type    = set(string)
  default = []
}
variable "version_adder_members" {
  type    = set(string)
  default = []
}
