#!/bin/bash

if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists, skipping init"
    cd frappe-bench
    bench start
    exit 0
fi

echo "Creating new bench..."
bench init --skip-redis-config-generation frappe-bench --version version-15

cd frappe-bench

# Use containers instead of localhost
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

# Remove redis, watch from Procfile
sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app telephony
bench get-app helpdesk --branch devops-ticketing --resolve-deps https://github.com/Amvnn/Frappe_ticketing_system-custom-.git

bench new-site helpdesk.localhost \
--force \
--mariadb-root-password 123 \
--admin-password admin \
--no-mariadb-socket

bench --site helpdesk.localhost install-app telephony
bench --site helpdesk.localhost install-app helpdesk
bench --site helpdesk.localhost set-config developer_mode 1
bench --site helpdesk.localhost set-config mute_emails 1
bench --site helpdesk.localhost set-config server_script_enabled 1
bench --site helpdesk.localhost set-config allow_tests true
bench --site helpdesk.localhost clear-cache
bench use helpdesk.localhost

# Install hypothesis for property-based tests
./env/bin/pip install hypothesis

# Run DevOps-specific setup (ticket types, custom fields, SLA, team, KB, saved replies)
echo ""
echo "Running DevOps ticketing system setup..."
bench --site helpdesk.localhost execute helpdesk.setup.devops_setup.run
echo "DevOps setup complete."
echo ""

bench start
