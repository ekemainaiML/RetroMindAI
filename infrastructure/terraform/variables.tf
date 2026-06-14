variable "region" {
  description = "OCI region (pick one with A1 Flex capacity)"
  default     = "eu-frankfurt-1"
}

variable "compartment_ocid" {
  description = "OCID of the compartment to deploy into"
}

variable "ssh_public_key" {
  description = "SSH public key for admin VM access"
}

variable "deploy_ssh_public_key" {
  description = "SSH public key for CI/CD deploy (GitHub Actions)"
  default     = ""
}

variable "admin_cidr" {
  description = "CIDR block allowed for SSH access"
  default     = "0.0.0.0/0"
}

variable "domain" {
  description = "Domain name (leave empty to skip DNS records)"
  default     = ""
}

variable "admin_email" {
  description = "Email for Let's Encrypt SSL certificate"
  default     = ""
}

variable "repo_url" {
  description = "Git repository URL for the application"
  default     = "https://github.com/ekemainaiML/RetroMindAI.git"
}

variable "data_volume_size_gb" {
  description = "Size of the block storage volume for uploads and models (GB)"
  default     = 50
}

variable "backup_access_duration_hours" {
  description = "Duration in hours for backup pre-authenticated request (0 to disable)"
  default     = 0
}

variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default = {
    "Project"   = "RetroMindAI"
    "ManagedBy" = "Terraform"
  }
}
