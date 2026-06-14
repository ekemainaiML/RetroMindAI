output "public_ip" {
  description = "VM public IP address"
  value       = oci_core_instance.app.public_ip
}

output "ssh_command" {
  description = "SSH command to access the VM"
  value       = "ssh -i /path/to/ssh_key ubuntu@${oci_core_instance.app.public_ip}"
}

output "deploy_host" {
  description = "SSH host string for GitHub Actions deploy workflow"
  value       = oci_core_instance.app.public_ip
}

output "bucket_uploads" {
  description = "Object storage bucket name for uploads"
  value       = oci_objectstorage_bucket.uploads.name
}

output "bucket_backups" {
  description = "Object storage bucket name for backups"
  value       = oci_objectstorage_bucket.backups.name
}

output "object_storage_namespace" {
  description = "Namespace for S3-compatible object storage endpoint"
  value       = data.oci_objectstorage_namespace.ns.namespace
}

output "s3_endpoint" {
  description = "S3-compatible endpoint URL for OCI Object Storage"
  value       = "https://${data.oci_objectstorage_namespace.ns.namespace}.compat.objectstorage.${var.region}.oraclecloud.com"
}

output "domain_name_servers" {
  description = "NS records to configure at your domain registrar"
  value       = var.domain != "" ? oci_dns_zone.main[0].nameservers : []
}

output "deploy_dir" {
  description = "Application directory on the VM"
  value       = local.deploy_dir
}

output "env_file_path" {
  description = "Path to the production environment file on the VM"
  value       = local.env_path
}

output "data_mount_point" {
  description = "Block volume mount point"
  value       = local.data_mount
}

output "instance_shape" {
  description = "Compute shape"
  value       = "VM.Standard.A1.Flex (4 OCPU, 24 GB RAM, ARM64)"
}

output "object_storage_api_endpoint" {
  description = "OCI API endpoint for object storage operations"
  value       = "https://objectstorage.${var.region}.oraclecloud.com"
}
