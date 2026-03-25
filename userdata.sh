#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip python3-venv git libpq-dev build-essential pkg-config awscli

# Get RDS endpoint dynamically from AWS
export AWS_DEFAULT_REGION=us-east-1
RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier turftime-db --query "DBInstances[0].Endpoint.Address" --output text 2>/dev/null)

cd /home/ubuntu
git clone https://github.com/vivekmenon2004/TurfTime.git
cd TurfTime
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn psycopg2-binary

# Run DB migrations
export USE_POSTGRES=true
export DB_HOST="$RDS_ENDPOINT"
export DB_NAME=turftimedb
export DB_USER=turftimeadmin
export DB_PASSWORD=TurfTime2026Secure
export DB_PORT=5432

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Setup Gunicorn systemd service with DB env vars
cat <<EOT > /etc/systemd/system/gunicorn.service
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/TurfTime
Environment="USE_POSTGRES=true"
Environment="DB_HOST=$RDS_ENDPOINT"
Environment="DB_NAME=turftimedb"
Environment="DB_USER=turftimeadmin"
Environment="DB_PASSWORD=TurfTime2026Secure"
Environment="DB_PORT=5432"
Environment="ALLOWED_HOSTS=*"
ExecStart=/home/ubuntu/TurfTime/venv/bin/gunicorn --access-logfile - --workers 3 --bind 0.0.0.0:8000 turftime_project.wsgi:application

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn
