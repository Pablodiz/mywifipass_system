#!/bin/bash

BASE_DIR="/etc/raddb/server_certs"
PENDING_DIR="$BASE_DIR/pending"
DELETION_DIR="$BASE_DIR/deletion"
PROCESSED_DIR="$BASE_DIR/processed"
LOG_DIR="$BASE_DIR/logs"

# Create directories if they don't exist
mkdir -p "$PENDING_DIR" "$PROCESSED_DIR" "$LOG_DIR"

CHANGES=0

for SSID_DIR in "$PENDING_DIR"/*/; do
  [ -d "$SSID_DIR" ] || continue
  SSID_DIR="${SSID_DIR%/}" # Remove trailing slash
  SSID=$(basename "$SSID_DIR")  
  echo "#################################### ADDING" >> "$LOG_DIR/$SSID.log"
  echo "Processing: $SSID" >> "$LOG_DIR/$SSID.log"

  # Verify files
  if [[ ! -f "$SSID_DIR/server.pem" || ! -f "$SSID_DIR/server.key" || ! -f "$SSID_DIR/ca.pem" ]]; then
    echo "Files are missing for $SSID" >> "$LOG_DIR/$SSID.log"
    continue # Skip this SSID
  fi

  # Create destination directory
  DEST_DIR="$BASE_DIR/$SSID"
  mkdir -p "$DEST_DIR"
  CA_DIR="$DEST_DIR/ca"
  mkdir -p "$CA_DIR"
  cp "$SSID_DIR/"server.pem "$DEST_DIR/" # Copy server cert 
  cp "$SSID_DIR/"ca.pem "$CA_DIR/" # Copy CA cert to ca_path
  cp "$SSID_DIR/"crl.pem "$CA_DIR/" # Copy CA cert to ca_path
  c_rehash "$CA_DIR" # Rehash the CA directory
  cp "$SSID_DIR/"*.key "$DEST_DIR/" # Copy server key

  # Execute the script to create the SSID in freeradius
  /usr/local/bin/create_ssids.sh "$SSID" >> "$LOG_DIR/$SSID.log" 2>&1

  # Move to processed directory
  mv --backup=numbered "$SSID_DIR/" "$PROCESSED_DIR/"  # To asure the move, instead of forcing with -f, we use --backup=numbered to avoid overwriting
  CHANGES=1
  echo "SSID $SSID processed" >> "$LOG_DIR/$SSID.log"
done

# Search each SSID file in the deletion directory
for SSID in "$DELETION_DIR"/*; do
  [ -f "$SSID" ] || continue
  SSID_NAME=$(basename "$SSID")
  echo "#################################### DELETING" >> "$LOG_DIR/$SSID_NAME.log"
  echo "Processing deletion for: $SSID_NAME" >> "$LOG_DIR/$SSID_NAME.log"

  # Remove the certs directory 
  DEST_DIR="$BASE_DIR/$SSID_NAME"
  if [ -d "$DEST_DIR" ]; then
    rm -rf "$DEST_DIR"
    echo "Deleted SSID $SSID_NAME from server_cert directory" >> "$LOG_DIR/$SSID_NAME.log"
  else
    echo "SSID $SSID_NAME not found in server_cert directory" >> "$LOG_DIR/$SSID_NAME.log"
  fi

  # Remove the SSID from FreeRADIUS
  /usr/local/bin/remove_ssids.sh "$SSID_NAME" >> "$LOG_DIR/$SSID_NAME.log" 2>&1
  
  rm $DELETION_DIR/$SSID_NAME # Remove the deletion file

  echo "Deleted SSID $SSID_NAME" >> "$LOG_DIR/$SSID_NAME.log"
  CHANGES=1
done

# Reboot FreeRADIUS
if [ $CHANGES -eq 1 ]; then
  echo "$(date) Changes detected, reloading FreeRADIUS..." >> "$LOG_DIR/reload.log"
  pkill -u freerad freeradius # We kill the process to force a restart of the container
fi 