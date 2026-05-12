#!/bin/bash
# Syncs local helpdesk code changes into the running container and runs tests.
# Usage: bash docker/sync-and-test.sh

CONTAINER="docker-frappe-1"
APP_PATH="/home/frappe/frappe-bench/apps/helpdesk"

echo "==> Syncing modified files to container..."

docker cp helpdesk/api/google_sso.py          $CONTAINER:$APP_PATH/helpdesk/api/google_sso.py
docker cp helpdesk/helpdesk/doctype/hd_settings/hd_settings.py \
                                               $CONTAINER:$APP_PATH/helpdesk/helpdesk/doctype/hd_settings/hd_settings.py
docker cp helpdesk/helpdesk/doctype/hd_settings/hd_settings.json \
                                               $CONTAINER:$APP_PATH/helpdesk/helpdesk/doctype/hd_settings/hd_settings.json
docker cp helpdesk/helpdesk/doctype/hd_google_sso_allowed_domain \
                                               $CONTAINER:$APP_PATH/helpdesk/helpdesk/doctype/

echo "==> Creating tests directory..."
docker exec $CONTAINER bash -c "mkdir -p $APP_PATH/helpdesk/tests && touch $APP_PATH/helpdesk/tests/__init__.py"

docker cp helpdesk/tests/test_google_sso.py   $CONTAINER:$APP_PATH/helpdesk/tests/test_google_sso.py
docker cp helpdesk/tests/test_slack.py        $CONTAINER:$APP_PATH/helpdesk/tests/test_slack.py

echo "==> Installing hypothesis..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && ./env/bin/pip install hypothesis -q"

echo "==> Enabling tests..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost set-config allow_tests true"

echo "==> Running Google SSO tests..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost run-tests --module helpdesk.tests.test_google_sso"
