#!/bin/bash
set -euo pipefail

# ── Striker Infrastructure: Provision / Destroy workhorse ──────────────
# Usage:
#   ./provision.sh up        # Create workhorse
#   ./provision.sh down      # Destroy workhorse (keep boot volume)
#   ./provision.sh status    # Show current state
#   ./provision.sh bake      # Create custom image from current workhorse
#   ./provision.sh sync      # rsync striker repo/results to workhorse
#   ./provision.sh run N     # Run N experiments in parallel via SSH
# ───────────────────────────────────────────────────────────────────────

TF_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_FILE="$TF_DIR/.terraform/terraform.tfstate"

# ── Helpers ────────────────────────────────────────────────────────────
tf() { terraform -chdir="$TF_DIR" "$@"; }

public_ip() {
  tf output -raw workhorse_public_ip 2>/dev/null || echo ""
}

# ── Commands ───────────────────────────────────────────────────────────

cmd_up() {
  echo "=== Provisioning research workhorse ==="
  tf init -input=false
  tf apply -auto-approve -var-file=variables.tfvars
  IP=$(public_ip)
  if [ -n "$IP" ]; then
    echo ""
    echo "✅ Workhorse is up at $IP"
    echo ""
    echo "  SSH:    ssh -o StrictHostKeyChecking=no x@$IP"
    echo "  Sync:   ./provision.sh sync"
    echo "  Run:    ./provision.sh run 8"
    echo "  Down:   ./provision.sh down"
  else
    echo "⚠️  Could not retrieve public IP. Check console."
  fi
}

cmd_down() {
  echo "=== Destroying research workhorse (boot volume preserved) ==="
  tf destroy -auto-approve -var-file=variables.tfvars
  echo ""
  echo "✅ Workhorse destroyed. Boot volume retained for next spin-up."
}

cmd_status() {
  echo "=== Workhorse Status ==="
  IP=$(public_ip)
  if [ -n "$IP" ]; then
    echo "  IP:     $IP"
    echo "  SSH:    ssh -o StrictHostKeyChecking=no x@$IP"
    # Try a quick health check
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 x@$IP "echo 'alive'" 2>/dev/null; then
      echo "  Status: ✅ Running"
    else
      echo "  Status: ⚠️  Unreachable or still provisioning"
    fi
  else
    echo "  Status: ❌ No running workhorse"
  fi
}

cmd_bake() {
  echo "=== Baking custom image from current workhorse ==="
  IP=$(public_ip)
  if [ -z "$IP" ]; then
    echo "❌ No running workhorse to bake. Run ./provision.sh up first."
    exit 1
  fi
  echo "Stopping services on workhorse..."
  ssh x@$IP "sudo systemctl stop hermes-gateway 2>/dev/null; sudo docker stop dragonfly 2>/dev/null; sync"
  echo ""
  echo "Creating image via OCI CLI (takes 10-20 min)..."
  # Get instance OCID from Terraform state
  INSTANCE_ID=$(tf output -raw workhorse_id 2>/dev/null)
  if [ -z "$INSTANCE_ID" ]; then
    echo "❌ Could not find instance OCID in state"
    exit 1
  fi
  echo "Instance OCID: $INSTANCE_ID"
  echo "Run: oci compute image create --instance-id $INSTANCE_ID --display-name striker-workhorse-$(date +%Y%m%d)"
  echo ""
  echo "Once the image is created, set its OCID in variables.tfvars:"
  echo "  image_ocid = \"ocid1.image.oc1.phx.xxxxx\""
}

cmd_sync() {
  IP=$(public_ip)
  if [ -z "$IP" ]; then
    echo "❌ Workhorse not running."
    exit 1
  fi
  echo "=== Syncing striker repo to workhorse ($IP) ==="
  rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    ~/striker/ x@$IP:/home/x/striker/
  echo ""
  echo "✅ Synced to $IP:/home/x/striker/"
}

cmd_run() {
  local N=${1:-4}
  local IP=$(public_ip)
  if [ -z "$IP" ]; then
    echo "❌ Workhorse not running."
    exit 1
  fi
  echo "=== Running $N experiments on workhorse ($IP) ==="
  ssh x@$IP "cd /home/x/striker && python3 scripts/parallel_experiments.py $N"
}

case "${1:-up}" in
  up)    cmd_up ;;
  down)  cmd_down ;;
  status) cmd_status ;;
  bake)  cmd_bake ;;
  sync)  cmd_sync ;;
  run)   cmd_run "${2:-4}" ;;
  *)     echo "Usage: $0 {up|down|status|bake|sync|run [N]}"; exit 1 ;;
esac
