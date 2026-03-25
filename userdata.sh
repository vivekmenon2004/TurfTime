#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3-pip python3-venv git libpq-dev build-essential pkg-config awscli

export AWS_DEFAULT_REGION=us-east-1

# Wait for RDS to be reachable (in case userdata runs before RDS is fully ready)
for i in {1..20}; do
    RDS_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier turftime-db --query "DBInstances[0].Endpoint.Address" --output text 2>/dev/null || echo "")
    if [ -n "$RDS_ENDPOINT" ] && [ "$RDS_ENDPOINT" != "None" ]; then
        break
    fi
    echo "Waiting for RDS endpoint... attempt $i"
    sleep 15
done

echo "Got RDS endpoint: $RDS_ENDPOINT"

cd /home/ubuntu
rm -rf TurfTime
git clone https://github.com/vivekmenon2004/TurfTime.git
cd TurfTime

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn psycopg2-binary

# Export env vars
export USE_POSTGRES=true
export DB_HOST="$RDS_ENDPOINT"
export DB_NAME=turftimedb
export DB_USER=turftimeadmin
export DB_PASSWORD=TurfTime2026Secure
export DB_PORT=5432
export ALLOWED_HOSTS="*"
export DEBUG=false

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Write Gunicorn systemd service with all env vars injected
cat > /etc/systemd/system/gunicorn.service <<EOT
[Unit]
Description=TurfTime Gunicorn daemon
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
Environment="DEBUG=false"
ExecStart=/home/ubuntu/TurfTime/venv/bin/gunicorn --access-logfile - --error-logfile - --workers 3 --bind 0.0.0.0:8000 turftime_project.wsgi:application
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn

echo "TurfTime deployment complete with RDS: $RDS_ENDPOINT"
