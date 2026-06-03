variable "region" {
  description = "OCI region (pick one with A1 capacity)"
  default     = "eu-frankfurt-1"
}

variable "compartment_ocid" {
  description = "OCID of the compartment to deploy into"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
}

variable "admin_cidr" {
  description = "CIDR block allowed for SSH"
  default     = "0.0.0.0/0"
}

variable "domain" {
  description = "Domain name (leave empty to skip DNS records)"
  default     = ""
}
