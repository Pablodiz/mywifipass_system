#!/bin/bash

DESTDIR="/etc/raddb/server_certs/$1/ca"

URI=$(openssl x509 -in "$DESTDIR/ca.pem" -noout -text | grep "URI:" | sed 's/URI://' | xargs)
if curl -f -s "$URI" -o "$DESTDIR/crl.pem"; then
    echo "CRL downloaded successfully for $1"
    c_rehash "$DESTDIR"  
else
    echo "Failed to download CRL for $1. Keeping the existing CRL (if any)."
    exit 1  
fi
