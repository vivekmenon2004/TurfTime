#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip python3-venv git libpq-dev build-essential pkg-config

RDS_ENDPOINT="turftime-db.ckjsi4eykdo2.us-east-1.rds.amazonaws.com"

cd /home/ubuntu
rm -rf TurfTime
git clone https://github.com/vivekmenon2004/TurfTime.git
cd TurfTime

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn psycopg2-binary

export USE_POSTGRES=true
export DB_HOST="$RDS_ENDPOINT"
export DB_NAME=turftimedb
export DB_USER=turftimeadmin
export DB_PASSWORD=TurfTime2026Secure
export DB_PORT=5432
export ALLOWED_HOSTS="*"
export DEBUG=false

python manage.py migrate --noinput || echo "Migrations failed, continuing..."
python manage.py collectstatic --noinput || echo "Collectstatic failed, continuing..."

cat > /etc/systemd/system/gunicorn.service <<EOT
[Unit]
Description=TurfTime Gunicorn
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/TurfTime
Environment="USE_POSTGRES=true"
Environment="DB_HOST=turftime-db.ckjsi4eykdo2.us-east-1.rds.amazonaws.com"
Environment="DB_NAME=turftimedb"
Environment="DB_USER=turftimeadmin"
Environment="DB_PASSWORD=TurfTime2026Secure"
Environment="DB_PORT=5432"
Environment="ALLOWED_HOSTS=*"
Environment="DEBUG=false"
ExecStart=/home/ubuntu/TurfTime/venv/bin/gunicorn --access-logfile - --error-logfile - --workers 3 --bind 0.0.0.0:8000 turftime_project.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn
echo "Deployment complete"
