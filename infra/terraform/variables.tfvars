# ── Terraform variables ───────────────────────────────────────────────
# Override values in terraform.tfvars or via environment variables

tenancy_ocid     = "ocid1.tenancy.oc1..aaaaaaaatkaazifcfqcdhpncclugfjjr2ylunfgf5xrmo7hdrja6svitja7a"
user_ocid        = "ocid1.user.oc1..aaaaaaaaki5jdqbeq5av6ph67mogbu6i7fo42cnhs3wqqmysviskqwmuwt3q"
fingerprint      = "21:c8:62:eb:19:13:e2:72:8e:97:b2:a2:a4:64:bc:d5"
private_key_path = "~/.oci/oci_api_key.pem"
region           = "us-phoenix-1"
compartment_ocid = "ocid1.tenancy.oc1..aaaaaaaatkaazifcfqcdhpncclugfjjr2ylunfgf5xrmo7hdrja6svitja7a"

shape           = "VM.Standard.E5.Flex"
ocpus           = 32
memory_in_gbs   = 128

# Leave empty to use latest Oracle Linux 9 image,
# or set to a custom image OCID after we've baked one.
image_ocid = ""

# SSH public keys (add Chase's key here)
ssh_keys = [
  # "ssh-ed25519 AAAA..."
]
