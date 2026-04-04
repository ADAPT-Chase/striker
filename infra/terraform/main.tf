# Terraform configuration for Oracle Cloud Infrastructure (OCI)
# Research Workhorse: VM.Standard.E5.Flex, 32 OCPU / 128 GB RAM
# Region: us-phoenix-1 (PHX)

terraform {
  required_version = ">= 1.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# ── Variables ──────────────────────────────────────────────────────────

variable "tenancy_ocid" {
  description = "OCI tenancy OCID"
  type        = string
}
variable "user_ocid" {
  description = "OCI user OCID"
  type        = string
}
variable "fingerprint" {
  description = "API key fingerprint"
  type        = string
}
variable "private_key_path" {
  description = "Path to the private API key"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}
variable "region" {
  description = "OCI region"
  type        = string
  default     = "us-phoenix-1"
}
variable "availability_domain" {
  description = "Availability domain for the compute instance"
  type        = string
  default     = ""
}
variable "shape" {
  description = "Compute shape"
  type        = string
  default     = "VM.Standard.E5.Flex"
}
variable "ocpus" {
  description = "Number of OCPUs"
  type        = number
  default     = 32
}
variable "memory_in_gbs" {
  description = "Memory in GB"
  type        = number
  default     = 128
}
variable "compartment_ocid" {
  description = "Compartment OCID (default: tenancy root)"
  type        = string
  default     = ""
}
variable "image_ocid" {
  description = "Custom image OCID (leave empty for latest Oracle Linux 9)"
  type        = string
  default     = ""
}
variable "source_boot_volume_id" {
  description = "Source boot volume OCID (if cloning from a snapshot)"
  type        = string
  default     = ""
}
variable "ssh_keys" {
  description = "SSH public keys for the instance"
  type        = list(string)
  default     = []
}

# ── Data sources ───────────────────────────────────────────────────────

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid != "" ? var.compartment_ocid : var.tenancy_ocid
}

locals {
  ad = var.availability_domain != "" ? var.availability_domain : data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_ocid = var.compartment_ocid != "" ? var.compartment_ocid : var.tenancy_ocid
}

# ── Network (VNIC) ────────────────────────────────────────────────────

resource "oci_core_vcn" "research_vcn" {
  cidr_block   = "10.0.0.0/16"
  compartment_id = local.compartment_ocid
  display_name = "research-workhorse-vcn"
  dns_label    = "research"
}

resource "oci_core_internet_gateway" "research_igw" {
  compartment_id = local.compartment_ocid
  display_name   = "research-igw"
  vcn_id         = oci_core_vcn.research_vcn.id
  enabled        = true
}

resource "oci_core_security_list" "research_sl" {
  compartment_id = local.compartment_ocid
  vcn_id         = oci_core_vcn.research_vcn.id
  display_name   = "research-scl"

  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "SSH"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol    = "6"
    source      = "10.0.0.0/16"
    description = "Internal communication"
    tcp_options {
      min = 1
      max = 65535
    }
  }

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    description = "Allow all outbound"
  }
}

resource "oci_core_subnet" "research_subnet" {
  cidr_block                 = "10.0.1.0/24"
  compartment_id             = local.compartment_ocid
  vcn_id                     = oci_core_vcn.research_vcn.id
  display_name               = "research-subnet"
  dns_label                  = "research"
  security_list_ids          = [oci_core_security_list.research_sl.id]
  route_table_id             = oci_core_route_table.research_rt.id
  prohibit_public_ip_on_vnic = false
}

resource "oci_core_route_table" "research_rt" {
  compartment_id = local.compartment_ocid
  vcn_id         = oci_core_vcn.research_vcn.id
  display_name   = "research-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.research_igw.id
  }
}

# ── Workhorse instance ────────────────────────────────────────────────

resource "oci_core_instance" "workhorse" {
  availability_domain = local.ad
  compartment_id      = local.compartment_ocid
  display_name        = "striker-research-workhorse"
  shape               = var.shape

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_in_gbs
  }

  create_vnic_details {
    subnet_id                 = oci_core_subnet.research_subnet.id
    assign_public_ip          = true
    display_name              = "workhorse-vnic"
    skip_source_dest_check    = false
  }

  # Prefer custom image if provided, otherwise source boot volume
  source_details {
    source_type   = var.image_ocid != "" ? "image" : (var.source_boot_volume_id != "" ? "bootVolume" : "image")
    source_id     = var.image_ocid != "" ? var.image_ocid : (var.source_boot_volume_id != "" ? var.source_boot_volume_id : "")
    boot_volume_size_in_gbs = 100
    # Keep the boot volume after destroy
    boot_volume_vpus_per_gb = 10
  }

  preserve_boot_volume = true

  metadata = {
    ssh_authorized_keys = join("\n", var.ssh_keys)
    user_data           = base64encode(templatefile("${path.module}/templates/cloud-init.yaml", {
      public_ip = oci_core_instance.workhorse.create_vnic_details[0].assign_public_ip ? "" : "will-set-later"
    }))
  }

  lifecycle {
    ignore_changes = [
      create_vnic_details[0].assign_public_ip,
      metadata["ssh_authorized_keys"],
    ]
  }
}

# ── Outputs ────────────────────────────────────────────────────────────

output "workhorse_public_ip" {
  description = "Public IP of the research workhorse"
  value       = oci_core_instance.workhorse.public_ip
}

output "workhorse_id" {
  description = "Instance OCID"
  value       = oci_core_instance.workhorse.id
}
