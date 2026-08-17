#!/usr/bin/env bash
# Generate a self-signed TLS cert for local/development use.
# Usage: ./generate-certs.sh [output_dir]
set -euo pipefail

OUT_DIR="${1:-$(dirname "$0")/certs}"
mkdir -p "$OUT_DIR"

if [[ -f "$OUT_DIR/server.crt" && -f "$OUT_DIR/server.key" ]]; then
  echo "Certs already exist in $OUT_DIR"
  exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$OUT_DIR/server.key" \
  -out    "$OUT_DIR/server.crt" \
  -days   365 \
  -subj   "/C=US/ST=Dev/L=Dev/O=RAGSYS/CN=ragsys.local"

chmod 600 "$OUT_DIR/server.key"
echo "Wrote self-signed cert to $OUT_DIR"
