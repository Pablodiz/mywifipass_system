#!/bin/bash

# Create the folder for the django secret key if it doesn't exist
if [ ! -d "/djangox509/mywifipass/secrets" ]; then
    mkdir -p /djangox509/mywifipass/secrets
fi

if [ ! -d "/djangox509/mywifipass/logos" ]; then
    mkdir -p /djangox509/mywifipass/logos
fi

if [ ! -f "/djangox509/mywifipass/secrets/.env" ]; then 
    touch /djangox509/mywifipass/secrets/.env
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