# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

#!/bin/bash

BASE_DIR="/etc/raddb/server_certs"
LOG_DIR="$BASE_DIR/logs"


# Procesar cada carpeta SSID existente
for SSID_DIR in "$BASE_DIR"/*/; do
  SSID_DIR="${SSID_DIR%/}" # Remove trailing slash
  SSID=$(basename "$SSID_DIR")

  # Ignorar carpetas estándar
  if [[ "$SSID" == "pending" || "$SSID" == "deletion" || "$SSID" == "processed" || "$SSID" == "update_crl" || "$SSID" == "logs" ]]; then
    continue
  fi

  echo "#################################### PERFORMING AUTOMATIC CRL UPDATES" >> "$LOG_DIR/$SSID.log"

  # Llamar al script update_crl.sh para cada SSID
  DEST_DIR="$BASE_DIR/$SSID/ca"
  if [ -d "$DEST_DIR" ]; then
      /usr/local/bin/update_crl.sh "$SSID" >> "$LOG_DIR/$SSID.log" 2>&1
      echo "Updated CRL for existing SSID $SSID" >> "$LOG_DIR/$SSID.log"
  else
      echo "$DEST_DIR not found for existing SSID $SSID" >> "$LOG_DIR/$SSID.log"
  fi
done

pkill -u freerad freeradius # We kill the process to force a restart of the container