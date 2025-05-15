#!/bin/bash

# Create the folder for the django secret key if it doesn't exist
if [ ! -d "/djangox509/getEAP_TLS/secrets" ]; then
    mkdir -p /djangox509/getEAP_TLS/secrets
fi

if [ ! -d "/djangox509/getEAP_TLS/logos" ]; then
    mkdir -p /djangox509/getEAP_TLS/logos
fi

if [ ! -f "/djangox509/getEAP_TLS/secrets/.env" ]; then 
    touch /djangox509/getEAP_TLS/secrets/.env
fi

# Prepare the database
echo "running migrations"
python3 manage.py makemigrations
python3 manage.py migrate
# Collect static files for the web server to use
python3 manage.py collectstatic --noinput
# Generate a superuser for the admin interface with a default password (admin)
echo "creating superuser (admin/admin)"
python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
EOF