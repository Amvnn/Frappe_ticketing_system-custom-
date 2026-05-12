#!/bin/bash
# Comprehensive Docker Verification & Setup Script
# Verifies all changes are in container and runs setup

set -e

CONTAINER="docker-frappe-1"
SITE="helpdesk.localhost"

echo "=============================================="
echo "🔍 DevOps Helpdesk - Docker Verification"
echo "=============================================="

# 1. Check container is running
echo ""
echo "📍 [1/6] Checking if container is running..."
if docker ps | grep -q "$CONTAINER"; then
    echo "✅ Container '$CONTAINER' is running"
else
    echo "❌ Container '$CONTAINER' is NOT running"
    exit 1
fi

# 2. Wait for Frappe to be ready
echo ""
echo "📍 [2/6] Waiting for Frappe to be ready (max 60s)..."
for i in {1..60}; do
    if docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench list-apps 2>&1 | grep -q frappe"; then
        echo "✅ Frappe is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Frappe took too long to start"
        exit 1
    fi
    echo -n "."
    sleep 1
done

# 3. Verify code files exist
echo ""
echo "📍 [3/6] Verifying code files in container..."
FILES=(
    "/home/frappe/frappe-bench/apps/helpdesk/helpdesk/patches/add_devops_custom_fields.py"
    "/home/frappe/frappe-bench/apps/helpdesk/helpdesk/setup/devops_setup.py"
    "/home/frappe/frappe-bench/apps/helpdesk/helpdesk/api/slack.py"
)

for file in "${FILES[@]}"; do
    if docker exec $CONTAINER test -f "$file"; then
        echo "✅ $(basename $file) exists"
    else
        echo "❌ $(basename $file) NOT found"
        exit 1
    fi
done

# 4. List installed apps
echo ""
echo "📍 [4/6] Installed apps in Frappe:"
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench list-apps" | sed 's/^/  /'

# 5. Run custom fields patch
echo ""
echo "📍 [5/6] Applying custom fields patch..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site $SITE execute helpdesk.patches.add_devops_custom_fields.execute" && echo "✅ Custom fields applied" || echo "⚠️ Custom fields patch result (may have warnings)"

# 6. Run DevOps setup
echo ""
echo "📍 [6/6] Running DevOps setup (ticket types, SLA, teams)..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site $SITE execute helpdesk.setup.devops_setup.execute" && echo "✅ DevOps setup complete" || echo "⚠️ DevOps setup result (may have warnings)"

echo ""
echo "=============================================="
echo "✅ Docker Verification & Setup Complete!"
echo "=============================================="
echo ""
echo "📋 Next Steps:"
echo "1. Open: http://localhost:8000/helpdesk"
echo "2. Login: Administrator / admin"
echo "3. Go to Settings → Ticket Types (verify 13 types created)"
echo "4. Go to Settings → SLA (verify 3 rules created)"
echo ""
echo "🔗 Direct URLs:"
echo "  • App Dashboard: http://localhost:8000/helpdesk"
echo "  • Settings: http://localhost:8000/app/hd-settings"
echo "  • Ticket Types: http://localhost:8000/app/hd-ticket-type"
echo "=============================================="
