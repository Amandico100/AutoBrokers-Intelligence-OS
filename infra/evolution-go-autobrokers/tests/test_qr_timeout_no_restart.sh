#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"
source_file="$root/pkg/whatsmeow/service/whatsmeow.go"
instance_file="$root/pkg/instance/service/instance_service.go"

if grep -q 'Restarting client' "$source_file"; then
  echo 'FAIL: QR/client teardown still restarts the client automatically' >&2
  exit 1
fi

if ! grep -q 'qr_expired' "$source_file"; then
  echo 'FAIL: QR timeout does not persist the terminal qr_expired reason' >&2
  exit 1
fi

if ! grep -q 'ErrorCode.*json:"errorCode,omitempty"' "$instance_file"; then
  echo 'FAIL: QR contract does not expose a normalized terminal errorCode' >&2
  exit 1
fi

if ! grep -q 'State.*json:"state,omitempty"' "$instance_file"; then
  echo 'FAIL: QR contract does not expose a normalized state' >&2
  exit 1
fi

echo 'PASS: QR timeout is terminal and exposes a normalized state'
