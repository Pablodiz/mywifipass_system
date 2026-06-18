#!/bin/bash
# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

DESTDIR="/etc/raddb/server_certs/$1/ca"
MAX_RETRIES=3
RETRY_DELAY=30

URI=$(openssl x509 -in "$DESTDIR/ca.pem" -noout -text | grep "URI:" | sed 's/URI://' | xargs)

for attempt in $(seq 1 $MAX_RETRIES); do
    if curl -f -s "$URI" -o "$DESTDIR/crl.pem"; then
        echo "CRL downloaded successfully for $1 (attempt $attempt/$MAX_RETRIES)"
        c_rehash "$DESTDIR"
        exit 0
    fi
    echo "CRL download attempt $attempt/$MAX_RETRIES failed for $1" >&2
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        sleep $RETRY_DELAY
    fi
done

echo "ERROR: all $MAX_RETRIES CRL download attempts failed for $1. Keeping existing CRL." >&2
exit 1
