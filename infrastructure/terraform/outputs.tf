output "public_ip" {
  description = "VM public IP"
  value       = oci_core_instance.app.public_ip
}

output "ssh_command" {
  description = "SSH command to access the VM"
  value       = "ssh ubuntu@${oci_core_instance.app.public_ip}"
}

output "bucket_uploads" {
  description = "Object storage bucket for uploads"
  value       = oci_objectstorage_bucket.uploads.name
}

output "bucket_backups" {
  description = "Object storage bucket for backups"
  value       = oci_objectstorage_bucket.backups.name
}

output "object_storage_namespace" {
  description = "Namespace for S3-compatible endpoint"
  value       = data.oci_objectstorage_namespace.ns.namespace
}

output "domain_name_servers" {
  description = "NS records to set at your registrar"
  value       = var.domain != "" ? oci_dns_zone.main[0].nameservers : []
}
