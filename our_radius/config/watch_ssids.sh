#!/bin/bash
# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

# Watches pending/, deletion/, and update_crl/ for new files and triggers
# process_ssids.sh immediately instead of waiting for the cron poll.

BASE_DIR="/etc/raddb/server_certs"

mkdir -p "$BASE_DIR/pending" "$BASE_DIR/deletion" "$BASE_DIR/update_crl"

echo "watch_ssids: starting inotifywait on $BASE_DIR/{pending,deletion,update_crl}"

while true; do
    inotifywait -q -e create,moved_to \
        "$BASE_DIR/pending" \
        "$BASE_DIR/deletion" \
        "$BASE_DIR/update_crl" \
        --format '%w%f'
    echo "watch_ssids: change detected, running process_ssids.sh"
    /usr/local/bin/process_ssids.sh
done
