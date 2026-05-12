# 🧪 Docker Container Testing & Verification Guide

## Quick Start Testing (5 minutes)

### 1. Verify Web Server is Accessible
```powershell
# Test from your machine
Invoke-WebRequest -Uri "http://localhost:8000/helpdesk" -TimeoutSec 5 | Select-Object StatusCode, StatusDescription
```

**Expected:** `StatusCode: 200, StatusDescription: OK`

---

### 2. Login and Verify App is Working

1. Open http://localhost:8000/helpdesk in your browser
2. **Username:** Administrator
3. **Password:** admin
4. Click "Login"

**Expected:** Dashboard loads with "Tickets" widget

---

### 3. Check Installed Apps

```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench list-apps"
```

**Expected Output:**
```
frappe    15.107.2  version-15
telephony 0.0.1    develop
helpdesk  1.24.1   main
```

---

### 4. Verify All Code Files are in Container

```bash
docker exec docker-frappe-1 bash -c "test -f /home/frappe/frappe-bench/apps/helpdesk/helpdesk/patches/add_devops_custom_fields.py && echo '✅ Custom fields patch exists' || echo '❌ Missing'"

docker exec docker-frappe-1 bash -c "test -f /home/frappe/frappe-bench/apps/helpdesk/helpdesk/setup/devops_setup.py && echo '✅ Setup script exists' || echo '❌ Missing'"

docker exec docker-frappe-1 bash -c "test -f /home/frappe/frappe-bench/apps/helpdesk/helpdesk/api/slack.py && echo '✅ Slack module exists' || echo '❌ Missing'"
```

**Expected:** All three ✅ checks pass

---

## Port Mapping Verification

### Check All Ports are Exposed

```powershell
# Check what ports are open
netstat -ano | Select-String "LISTENING" | Select-String "8000|9000"
```

**Expected:** Ports 8000 and 9000 listening on 0.0.0.0

---

### Test Each Port

#### Port 8000 (Frappe Web)
```powershell
Test-NetConnection -ComputerName localhost -Port 8000 -InformationLevel Quiet
# Or visit: http://localhost:8000
```

#### Port 9000 (Socket.io)
```bash
# From container
docker exec docker-frappe-1 bash -c "curl -s http://localhost:9000 | head -c 50"
```

---

## Apply Configuration Changes

### Command 1: Add Custom Fields
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost execute helpdesk.patches.add_devops_custom_fields.execute"
```

**Verify in UI:**
- Open http://localhost:8000/app/hd-ticket/new
- Should see new fields under "DevOps Information" section

### Command 2: Create Ticket Types & SLA Rules
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost execute helpdesk.setup.devops_setup.execute"
```

**Verify in UI:**
1. Open http://localhost:8000/app/hd-ticket-type
   - Should see 13 types: CI/CD Pipeline, Server, Database, etc.

2. Open http://localhost:8000/app/hd-service-level-agreement
   - Should see 3 SLA rules: High, Medium, Low

3. Open http://localhost:8000/app/hd-team
   - Should see "DevOps" team created

---

## Container Health Checks

### Check All Services Running
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected:**
```
NAMES              STATUS              PORTS
docker-frappe-1    Up (hours)          0.0.0.0:8000->8000/tcp, 0.0.0.0:9000->9000/tcp
docker-mariadb-1   Up (hours)          3306/tcp
docker-redis-1     Up (hours)          6379/tcp
```

### Check Logs for Errors
```bash
# Last 20 lines
docker logs docker-frappe-1 | Select-Object -Last 20

# Watch live logs
docker logs -f docker-frappe-1
```

**Expected:** No ERROR lines, only INFO and WARNING messages

### Check Database Connection
```bash
# Connect to MySQL
docker exec docker-mariadb-1 mysql -uroot -p123 -e "SELECT 1;"
```

**Expected Output:**
```
+---+
| 1 |
+---+
| 1 |
+---+
```

---

## Test API Endpoints

### 1. Test Frappe API (Get Ticket List)
```bash
curl -s http://localhost:8000/api/resource/HD%20Ticket | jq . | Select-Object -First 30
```

### 2. Test Authentication
```bash
# Get auth token (replace password)
curl -s -X POST http://localhost:8000/api/auth \
  -H "Content-Type: application/json" \
  -d '{"usr":"Administrator","pwd":"admin"}' | jq .
```

### 3. Create Test Ticket via API
```bash
curl -X POST http://localhost:8000/api/resource/HD%20Ticket \
  -H "Authorization: Bearer [token]" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test Ticket",
    "description": "Testing from API",
    "priority": "High",
    "ticket_type": "CI/CD Pipeline"
  }'
```

---

## Troubleshooting

### Issue: "Connection refused" on port 8000

**Check container logs:**
```bash
docker logs docker-frappe-1 2>&1 | tail -20
```

**Restart container:**
```bash
cd docker && docker compose restart frappe
```

---

### Issue: "Module not found" errors

**Verify file exists:**
```bash
docker exec docker-frappe-1 bash -c "ls -la /home/frappe/frappe-bench/apps/helpdesk/helpdesk/patches/"
```

**If missing, copy file:**
```bash
docker cp helpdesk/patches/add_devops_custom_fields.py docker-frappe-1:/home/frappe/frappe-bench/apps/helpdesk/helpdesk/patches/
```

---

### Issue: Database connection failed

**Check MariaDB is running:**
```bash
docker ps | Select-String mariadb
```

**Check database is accessible:**
```bash
docker exec docker-mariadb-1 mysql -uroot -p123 -e "SHOW DATABASES;"
```

---

### Issue: Port already in use

**Find what's using the port:**
```powershell
netstat -ano | Select-String "8000|9000"
```

**Change port in docker-compose.yml:**
```yaml
ports:
  - "8001:8000"  # Changed from 8000
  - "9001:9000"  # Changed from 9000
```

Then restart: `docker compose down && docker compose up -d`

---

## Performance Testing

### Load Frappe App (Check Response Time)
```bash
# Measure response time
$url = "http://localhost:8000/helpdesk"
$timer = [System.Diagnostics.Stopwatch]::StartNew()
$response = Invoke-WebRequest -Uri $url
$timer.Stop()
Write-Host "Response time: $($timer.ElapsedMilliseconds)ms"
```

**Expected:** < 1000ms for initial load

### Check Container Resources
```bash
docker stats docker-frappe-1 --no-stream
```

**Expected:**
- CPU: < 20%
- Memory: < 500MB
- I/O: Minimal

---

## Smoke Test Checklist

Mark these as you verify:

- [ ] Web server accessible (http://localhost:8000)
- [ ] Can login with Administrator/admin
- [ ] Port 8000 responds to requests
- [ ] Port 9000 is open (Socket.io)
- [ ] Database is connected and healthy
- [ ] Redis cache is connected
- [ ] All 3 apps installed (frappe, telephony, helpdesk)
- [ ] Custom fields patch file exists
- [ ] Setup scripts exist
- [ ] Slack module exists
- [ ] No ERROR lines in container logs
- [ ] Dashboard loads with widgets

---

## Final Verification Command

Run this complete check:

```bash
#!/bin/bash
echo "🔍 Running comprehensive verification..."

# 1. Container running
docker ps | grep -q docker-frappe-1 && echo "✅ Container running" || echo "❌ Container not running"

# 2. Web server responsive
curl -s -o /dev/null -w "✅ Web server: %{http_code}\n" http://localhost:8000/

# 3. Apps installed
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench list-apps | grep -q helpdesk" && echo "✅ Helpdesk app installed" || echo "❌ Helpdesk not found"

# 4. Custom fields patch exists
docker exec docker-frappe-1 test -f /home/frappe/frappe-bench/apps/helpdesk/helpdesk/patches/add_devops_custom_fields.py && echo "✅ Custom fields patch ready" || echo "❌ Patch missing"

# 5. Setup scripts exist
docker exec docker-frappe-1 test -f /home/frappe/frappe-bench/apps/helpdesk/helpdesk/setup/devops_setup.py && echo "✅ Setup script ready" || echo "❌ Setup script missing"

# 6. Slack module exists
docker exec docker-frappe-1 test -f /home/frappe/frappe-bench/apps/helpdesk/helpdesk/api/slack.py && echo "✅ Slack module ready" || echo "❌ Slack module missing"

echo ""
echo "✅ All verifications complete!"
```

---

## Next Steps After Verification

1. ✅ Verify all checks pass
2. Run configuration migrations (custom fields & setup)
3. Create test ticket in UI
4. Configure email notifications
5. Set up Slack integration
6. Train team on usage

---

**Good luck! Your DevOps ticketing system is ready! 🚀**
