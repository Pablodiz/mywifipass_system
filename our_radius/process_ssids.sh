#!/bin/bash

BASE_DIR="/etc/raddb/server_certs"
PENDING_DIR="$BASE_DIR/pending"
PROCESSED_DIR="$BASE_DIR/processed"
LOG_DIR="$BASE_DIR/logs"

# Create directories if they don't exist
mkdir -p "$PENDING_DIR" "$PROCESSED_DIR" "$LOG_DIR"

CHANGES=0

for SSID_DIR in "$PENDING_DIR"/*/; do
  [ -d "$SSID_DIR" ] || continue
  SSID_DIR="${SSID_DIR%/}" # Remove trailing slash
  SSID=$(basename "$SSID_DIR")
  echo "Processing: $SSID" >> "$LOG_DIR/$SSID.log"

  # Verify files
  if [[ ! -f "$SSID_DIR/server.pem" || ! -f "$SSID_DIR/server.key" || ! -f "$SSID_DIR/ca.pem" ]]; then
    echo "Files are missing for $SSID" >> "$LOG_DIR/$SSID.log"
    continue
  fi

  # Create destination directory
  DEST_DIR="$BASE_DIR/$SSID"
  mkdir -p "$DEST_DIR"
  cp "$SSID_DIR/"*.pem "$DEST_DIR/" # Copy CA and server certs
  cp "$SSID_DIR/"*.key "$DEST_DIR/" # Copy server key

  # Execute the script to create the SSID in freeradius
  /usr/local/bin/create_ssids.sh "$SSID" >> "$LOG_DIR/$SSID.log" 2>&1

  # Move to processed directory
  mv "$SSID_DIR" "$PROCESSED_DIR/" 
  CHANGES=1
  echo "SSID $SSID processed" >> "$LOG_DIR/$SSID.log"
done

# Reboot FreeRADIUS
if [ $CHANGES -eq 1 ]; then
  echo "Changes detected, reloading FreeRADIUS..." >> "$LOG_DIR/reload.log"
  pkill -u freerad freeradius # We kill the process to force a restart of the container
fi 