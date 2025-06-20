#!/bin/bash
set -e 

if [ ! -f /etc/raddb/secret/secret.txt ]; then
    dd if=/dev/random bs=1 count=24 | base64 > /etc/raddb/secret/secret.txt
fi
