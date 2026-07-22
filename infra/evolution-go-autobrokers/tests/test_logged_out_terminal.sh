#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"
source_file="$root/pkg/whatsmeow/service/whatsmeow.go"

if ! grep -q 're_pair_required' "$source_file"; then
  echo 'FAIL: LoggedOut is not normalized to re_pair_required' >&2
  exit 1
fi

if grep -q 'Restarting client' "$source_file"; then
  echo 'FAIL: kill/LoggedOut path still performs an automatic restart' >&2
  exit 1
fi

if ! grep -q 'Unpaired client disconnected; waiting for an explicit pairing attempt' "$source_file"; then
  echo 'FAIL: disconnected unpaired clients are not terminal' >&2
  exit 1
fi

echo 'PASS: LoggedOut and disconnected unpaired clients are terminal'
