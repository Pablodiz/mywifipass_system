#!/bin/bash

echo "running migrations"
python3 manage.py migrate
echo "creating superuser (admin/password123)"
python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'password123')
EOF
#echo "starting development server"
#python3 manage.py runserver 0.0.0.0:8000
echo "waiting for your conection"
sleep infinity 
