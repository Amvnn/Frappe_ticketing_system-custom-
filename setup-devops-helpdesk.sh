#!/bin/bash
# Quick Setup Script for DevOps Ticketing System
# Run this after Docker containers are healthy
# Usage: bash ./setup-devops-helpdesk.sh

set -e

SITE="helpdesk.localhost"
CONTAINER="docker-frappe-1"

echo "================================================"
echo "🚀 DevOps Helpdesk Setup Script"
echo "================================================"

# Step 1: Apply custom fields
echo ""
echo "📍 Step 1/3: Applying custom fields..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site $SITE execute helpdesk.patches.add_devops_custom_fields.execute"

# Step 2: Create ticket types and SLA rules
echo ""
echo "📍 Step 2/3: Creating ticket types, SLA rules, and teams..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site $SITE execute helpdesk.setup.devops_setup.execute"

# Step 3: Clear cache and rebuild
echo ""
echo "📍 Step 3/3: Clearing cache and rebuilding..."
docker exec $CONTAINER bash -c "cd /home/frappe/frappe-bench && bench --site $SITE clear-cache && bench build --app helpdesk"

echo ""
echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "📋 Next Steps:"
echo "1. Open: http://helpdesk.localhost:8000/app/hd-settings"
echo "2. Configure working hours and holidays"
echo "3. Set up email account for notifications"
echo "4. Add team members to DevOps team"
echo ""
echo "👤 Login:"
echo "   Username: Administrator"
echo "   Password: admin"
echo ""
echo "📚 Full guide: See DEVOPS_SETUP_GUIDE.md"
echo "================================================"
