#!/usr/bin/env bash
set -euo pipefail

FOSSIL_CHECKOUT="${FOSSIL_CHECKOUT:-/mnt/usb/ltst-data}"
APP_ROOT="${APP_ROOT:-/mnt/usb/la-trobe-student-theatre-history}"
SQLITE_FILE="${SQLITE_FILE:-ltst.sqlite}"
SERVICE_NAME="${SERVICE_NAME:-ltst-catalog}"

if [[ ! -d "$FOSSIL_CHECKOUT" ]]; then
  echo "Error: Fossil checkout not found: $FOSSIL_CHECKOUT" >&2
  exit 1
fi

if [[ ! -d "$APP_ROOT" ]]; then
  echo "Error: app root not found: $APP_ROOT" >&2
  exit 1
fi

echo "Updating Fossil checkout at $FOSSIL_CHECKOUT..."
(
  cd "$FOSSIL_CHECKOUT"
  fossil update
)

SRC="$FOSSIL_CHECKOUT/$SQLITE_FILE"
DST="$APP_ROOT/$SQLITE_FILE"

if [[ ! -f "$SRC" ]]; then
  echo "Error: database not found in Fossil checkout: $SRC" >&2
  exit 1
fi

cp "$SRC" "$DST"
echo "Copied $SRC -> $DST"

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
  sudo systemctl restart "$SERVICE_NAME"
  echo "Restarted $SERVICE_NAME"
elif systemctl list-unit-files "$SERVICE_NAME.service" 2>/dev/null | grep -q "$SERVICE_NAME.service"; then
  sudo systemctl restart "$SERVICE_NAME"
  echo "Restarted $SERVICE_NAME"
else
  echo "Note: systemd unit $SERVICE_NAME not installed; copy deploy/ltst-catalog.service to enable auto-restart"
fi
