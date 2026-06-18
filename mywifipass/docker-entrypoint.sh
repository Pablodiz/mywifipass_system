#!/bin/bash

# Create the folder for the django secret key if it doesn't exist
if [ ! -d "/djangox509/mywifipass/secrets" ]; then
    mkdir -p /djangox509/mywifipass/secrets
fi

if [ ! -d "/djangox509/mywifipass/logos" ]; then
    mkdir -p /djangox509/mywifipass/logos
fi

if [ ! -f "/djangox509/mywifipass/secrets/.env" ] || ! grep -q "DJANGO_SECRET_KEY=" "/djangox509/mywifipass/secrets/.env"; then 
    echo "Generating new DJANGO_SECRET_KEY in secrets/.env..."
    SECRET=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    echo "DJANGO_SECRET_KEY=\"$SECRET\"" >> /djangox509/mywifipass/secrets/.env
    chmod 600 /djangox509/mywifipass/secrets/.env
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