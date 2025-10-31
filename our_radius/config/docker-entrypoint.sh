#!/bin/bash
# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.
set -e 

if [ ! -f /etc/raddb/secret/secret.txt ]; then
    dd if=/dev/random bs=1 count=24 | base64 > /etc/raddb/secret/secret.txt
fi
