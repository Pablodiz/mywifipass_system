#!/bin/bash


if [ "$1" == "makemigrations" ]; then
    echo "generating migrations"
    python3 manage.py makemigrations getEAP_TLS;
fi

echo "running migrations"
python3 manage.py migrate
echo "creating superuser (admin/password123)"
python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'password123')
EOF

if [ "$1" == "run" ]; then
    echo "running server"
    exec python3 manage.py runserver 0.0.0.0:8000
else 
    echo "waiting for your conection"
    sleep infinity 
fi 