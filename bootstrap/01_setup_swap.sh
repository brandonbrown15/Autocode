#!/usr/bin/env bash
# Optional NVMe swapfile (4–8 GB). Run with sudo on the Jetson.
set -euo pipefail

SIZE_GB="${1:-8}"
SWAPFILE="${SWAPFILE:-/swapfile}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0 [$SIZE_GB]"
  exit 1
fi

if swapon --show | grep -q .; then
  echo "Swap already active:"
  swapon --show
  exit 0
fi

fallocate -l "${SIZE_GB}G" "$SWAPFILE" || dd if=/dev/zero of="$SWAPFILE" bs=1G count="$SIZE_GB"
chmod 600 "$SWAPFILE"
mkswap "$SWAPFILE"
swapon "$SWAPFILE"

if ! grep -q "$SWAPFILE" /etc/fstab; then
  echo "$SWAPFILE none swap sw 0 0" >> /etc/fstab
fi

echo "Swap ${SIZE_GB}G enabled at $SWAPFILE"
