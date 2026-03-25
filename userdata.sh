#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-pip python3-venv git default-libmysqlclient-dev build-essential pkg-config
cd /home/ubuntu
git clone https://github.com/vivekmenon2004/TurfTime.git
cd TurfTime
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# Setup Gunicorn service
cat <<EOT >> /etc/systemd/system/gunicorn.service
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/TurfTime
ExecStart=/home/ubuntu/TurfTime/venv/bin/gunicorn --access-logfile - --workers 3 --bind 0.0.0.0:8000 turftime_project.wsgi:application

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn
