# DevOps Helpdesk - Quick Reference Card

## 🎯 URLs

| Purpose | URL | Username | Password |
|---------|-----|----------|----------|
| Agent Dashboard | `http://helpdesk.localhost:8000/helpdesk` | Administrator | admin |
| Helpdesk Settings | `http://helpdesk.localhost:8000/app/hd-settings` | Administrator | admin |
| Requester Portal | `http://helpdesk.localhost:8000/support` | (Any user) | (Their password) |
| Frappe Desk | `http://helpdesk.localhost:8000/app` | Administrator | admin |

---

## 🛠️ Common Docker Commands

### View Logs
```bash
docker logs docker-frappe-1 -f --tail=100
```

### Execute Bench Commands
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench [command]"
```

### Access Database
```bash
docker exec docker-mariadb-1 mysql -uroot -p123 helpdesk
```

### Stop/Start
```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
```

---

## 📝 Common Operations

### Create a Test User
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost add-user john@example.com John Doe --password password123 --roles Agent"
```

### Add User to DevOps Team (via API)
```bash
curl -X POST http://helpdesk.localhost:8000/api/resource/HD%20Team%20Member \
  -H "Content-Type: application/json" \
  -H "X-Frappe-CSRF-Token: [token]" \
  -d '{"team": "DevOps", "user": "john@example.com"}'
```

### Check System Health
```bash
curl http://helpdesk.localhost:8000/api/method/frappe.handler.ping
# Should return: "pong"
```

### View All Tickets (API)
```bash
curl http://helpdesk.localhost:8000/api/resource/HD%20Ticket \
  -H "Authorization: Bearer [auth_token]"
```

---

## 🔑 Configuration Files

| File | Purpose |
|------|---------|
| `docker/docker-compose.yml` | Container setup |
| `docker/init.sh` | Initial setup script |
| `helpdesk/patches/add_devops_custom_fields.py` | Custom fields migration |
| `helpdesk/setup/devops_setup.py` | Ticket types, SLA, teams |
| `helpdesk/api/slack.py` | Slack integration |
| `DEVOPS_SETUP_GUIDE.md` | Full setup walkthrough |

---

## 🎫 Ticket Types (Pre-configured)

1. CI/CD Pipeline
2. Server / Infrastructure
3. Database
4. Deployment Request
5. Access & Permissions
6. Environment Setup
7. Security / Credentials
8. Network / VPN
9. Monitoring & Alerts
10. Performance Issue
11. Data Migration
12. Backup & Recovery
13. Other

---

## 📊 SLA Rules (Pre-configured)

| Priority | Response | Resolution | Working Hours |
|----------|----------|------------|----------------|
| High | 1 hour | 4 hours | 24/7 |
| Medium | 4 hours | 1 day | Business only |
| Low | 1 day | 3 days | Business only |

---

## 🚀 Custom Fields (DevOps)

### Public (Requester sees)
- Department / Branch
- Project Name
- Environment (Dev/Staging/Prod)
- Impact Scope (User/Team/Service/Company)
- Error Code
- Affected Service

### Internal (DevOps only)
- Internal Notes
- Root Cause
- Resolution Steps Taken
- How to Prevent in Future

---

## 🔗 API Endpoints

### Create Ticket
```bash
POST /api/resource/HD%20Ticket
{
  "subject": "API server down",
  "description": "Getting 503 errors",
  "priority": "High",
  "ticket_type": "Server / Infrastructure",
  "environment": "Production"
}
```

### Get Ticket
```bash
GET /api/resource/HD%20Ticket/HD-0001
```

### Update Ticket Status
```bash
PUT /api/resource/HD%20Ticket/HD-0001
{
  "status": "Resolved",
  "root_cause": "Memory leak in service X"
}
```

### List All Tickets (Paginated)
```bash
GET /api/resource/HD%20Ticket?fields=["name","subject","status"]&limit_page_length=20
```

### Search Tickets
```bash
GET /api/resource/HD%20Ticket?filters=[["status","!=","Closed"]]&order_by=creation%20desc
```

### Create Slack Ticket
```bash
POST /api/method/helpdesk.api.slack.handle_ticket_command
(Sent from Slack slash command - automatic)
```

---

## 🐛 Troubleshooting

### "No such site: helpdesk.localhost"
**Solution:** Site may not be created. Check Docker logs:
```bash
docker logs docker-frappe-1 | grep -i "error"
```

### "Module not found: helpdesk.patches"
**Solution:** Pull latest code and rebuild:
```bash
cd helpdesk && git pull && docker exec docker-frappe-1 bench build --app helpdesk
```

### "Cannot reach helpdesk.localhost"
**Solution:** Add to hosts file (`C:\Windows\System32\drivers\etc\hosts`):
```
127.0.0.1 helpdesk.localhost
```

### Slack not connecting
**Solution:** Verify in custom settings (Settings → Custom Settings):
```json
{
  "slack_bot_token": "xoxb-...",
  "slack_signing_secret": "..."
}
```

---

## 📞 Support

- **Frappe Docs:** https://docs.frappe.io/helpdesk
- **GitHub Issues:** https://github.com/frappe/helpdesk/issues
- **Frappe Forum:** https://discuss.frappe.io/c/frappehelpdesk

---

## 🎓 Learning Paths

### For Agents
1. Access `/helpdesk` dashboard
2. Understand ticket lifecycle
3. Use saved views and filters
4. Learn @ mentions and internal notes
5. Track SLA metrics

### For Administrators
1. Configure custom fields
2. Set up SLA rules and teams
3. Create notification templates
4. Integrate with Slack/email
5. Generate reports

### For Developers (Customization)
1. Study `helpdesk/api/` modules
2. Learn Frappe ORM (`helpdesk/hooks.py`)
3. Create custom API endpoints
4. Add Vue components (`desk/src/components/`)
5. Write server scripts for automation

---

*Last Updated: May 2026*
*Version: Frappe Helpdesk 1.24.1 + DevOps Customization*
