terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0"
    }
  }
}

provider "oci" {
  region = var.region
}

# ── Networking ──────────────────────────────────────────────

resource "oci_core_vcn" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "retromind-vcn"
  cidr_block     = "10.0.0.0/16"
  dns_label      = "retromind"
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.main.id
  display_name      = "retromind-public"
  cidr_block        = "10.0.1.0/24"
  dns_label         = "public"
  security_list_ids = [oci_core_security_list.public.id]
  route_table_id    = oci_core_route_table.public.id
}

resource "oci_core_internet_gateway" "main" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "retromind-igw"
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "retromind-public-rt"
  route_rules {
    network_entity_id = oci_core_internet_gateway.main.id
    destination       = "0.0.0.0/0"
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.main.id
  display_name   = "retromind-public-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "HTTP"
    tcp_options { max = 80; min = 80 }
  }
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "HTTPS"
    tcp_options { max = 443; min = 443 }
  }
  ingress_security_rules {
    protocol    = "6"
    source      = var.admin_cidr
    description = "SSH"
    tcp_options { max = 22; min = 22 }
  }
}

# ── Compute ─────────────────────────────────────────────────

resource "oci_core_instance" "app" {
  compartment_id      = var.compartment_ocid
  display_name        = "retromind-app"
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  shape               = "VM.Standard.A1.Flex"
  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = 150
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "app"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  preserve_boot_volume = false
}

# ── Block Storage (uploads & models) ────────────────────────

resource "oci_core_volume" "data" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "retromind-data"
  size_in_gbs         = 50
}

resource "oci_core_volume_attachment" "data" {
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.app.id
  volume_id       = oci_core_volume.data.id
  device          = "/dev/oracleoci/oraclevdb"
}

# ── Object Storage ──────────────────────────────────────────

resource "oci_objectstorage_bucket" "uploads" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  name           = "retromind-uploads"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
}

resource "oci_objectstorage_bucket" "backups" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  name           = "retromind-backups"
  access_type    = "NoPublicAccess"
  storage_tier   = "Archive"
}

# ── DNS ─────────────────────────────────────────────────────

resource "oci_dns_zone" "main" {
  count        = var.domain != "" ? 1 : 0
  compartment_id = var.compartment_ocid
  name         = var.domain
  zone_type    = "PRIMARY"
}

resource "oci_dns_rrset" "app" {
  count       = var.domain != "" ? 1 : 0
  zone_name_or_id = oci_dns_zone.main[0].id
  domain      = var.domain
  rtype       = "A"
  rtype_version = "1"
  items {
    domain = var.domain
    rtype  = "A"
    rdata  = oci_core_instance.app.public_ip
    ttl    = 300
  }
}

resource "oci_dns_rrset" "api" {
  count       = var.domain != "" ? 1 : 0
  zone_name_or_id = oci_dns_zone.main[0].id
  domain      = "api.${var.domain}"
  rtype       = "A"
  rtype_version = "1"
  items {
    domain = "api.${var.domain}"
    rtype  = "A"
    rdata  = oci_core_instance.app.public_ip
    ttl    = 300
  }
}

# ── Data Sources ────────────────────────────────────────────

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_objectstorage_namespace" "ns" {
  compartment_id = var.compartment_ocid
}
