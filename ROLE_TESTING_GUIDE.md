# Role-Based Testing Guide — DevOps Ticketing System

Site: http://helpdesk.localhost:8000
Default admin: Administrator / admin

This guide walks you through testing every role in the system with exact steps,
what you should see, and what you should NOT be able to do.

---

## Container Status Check

Before testing, confirm the container is ready:

```bash
# Check all 3 containers are Up
docker ps

# Check all 4 bench processes are running (web, socketio, schedule, worker)
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && cat Procfile"

# Quick health check
curl -s http://helpdesk.localhost:8000/api/method/ping
# Expected: {"message":"pong"}
```

---

## Test User Setup (run once as Administrator)

Before role testing, create one user per role. Do this in the Frappe Desk.

```
1. Log in: http://helpdesk.localhost:8000 → Administrator / admin
2. Go to: http://helpdesk.localhost:8000/app/user/new-user-1
```

Create these 4 users:

| Full Name | Email | Password | Role to assign |
|---|---|---|---|
| DevOps Lead | lead@helpdesk.localhost | Test@1234 | Agent Manager |
| DevOps Engineer | engineer@helpdesk.localhost | Test@1234 | Agent |
| Developer User | developer@helpdesk.localhost | Test@1234 | (none — Customer by default) |
| IT Admin | admin2@helpdesk.localhost | Test@1234 | System Manager |

For each user:
- New User form → fill Email, First Name, New Password
- Roles tab → Add Row → select the role
- Save

For the Agent and Agent Manager users, also invite them as agents:
- Go to http://helpdesk.localhost:8000/helpdesk
- Settings > Agents > Invite Agents → enter their emails

---

## Role 1: Administrator

**Login:** Administrator / admin
**Portal:** http://helpdesk.localhost:8000/helpdesk (agent desk)
**Also has access to:** http://helpdesk.localhost:8000/app (Frappe Desk — full backend)

### What you can do

- [ ] Access Frappe Desk (http://helpdesk.localhost:8000/app) — full backend access
- [ ] Access agent desk (http://helpdesk.localhost:8000/helpdesk)
- [ ] See ALL tickets from all users
- [ ] Configure Google SSO: Settings > Integrations > Google SSO
- [ ] Configure Slack: Settings > Integrations > Slack
- [ ] Create/edit/delete any user
- [ ] Assign any role to any user
- [ ] Configure email accounts
- [ ] View and edit HD Settings
- [ ] Create ticket types, SLA policies, assignment rules
- [ ] Access all reports and dashboards

### What to verify

```
1. Open http://helpdesk.localhost:8000/app
   Expected: Full Frappe Desk loads with all modules

2. Open http://helpdesk.localhost:8000/helpdesk
   Expected: Agent desk loads with full ticket queue

3. Settings > Integrations > Google SSO
   Expected: Toggle, Client ID, Client Secret, Allowed Domains fields visible

4. Settings > Integrations > Slack
   Expected: Bot Token, Signing Secret fields visible

5. Create a test ticket via the API:
   http://helpdesk.localhost:8000/api/method/frappe.client.insert
   (or use the customer portal as a different user)
   Expected: Ticket appears in agent desk queue
```

---

## Role 2: System Manager (IT Admin)

**Login:** admin2@helpdesk.localhost / Test@1234
**Portal:** http://helpdesk.localhost:8000/helpdesk (agent desk)

### What you can do

- [ ] Access agent desk — see all tickets
- [ ] Configure all settings (SSO, Slack, SLA, email, assignment rules)
- [ ] Invite agents
- [ ] Create/manage teams
- [ ] View dashboard and reports
- [ ] Cannot access raw Frappe Desk backend (unless also given System Manager in Frappe)

### What to verify

```
1. Log in as admin2@helpdesk.localhost
   Expected: Agent desk loads

2. Settings > Integrations > Google SSO
   Expected: All fields editable, Save button works

3. Settings > Agents
   Expected: Can see agent list, Invite Agents button works

4. Settings > SLA Policies
   Expected: Can create/edit SLA policies

5. Settings > Assignment Rules
   Expected: Can create/edit assignment rules

6. Try to access http://helpdesk.localhost:8000/app
   Expected: May redirect or show limited access (not full Frappe Desk)
```

---

## Role 3: Agent Manager (DevOps Lead)

**Login:** lead@helpdesk.localhost / Test@1234
**Portal:** http://helpdesk.localhost:8000/helpdesk (agent desk)

### What you can do

- [ ] See ALL tickets (not just assigned to them)
- [ ] Assign/reassign tickets to any agent
- [ ] View full dashboard with team metrics
- [ ] Manage agents and teams
- [ ] Reply to tickets, leave internal notes
- [ ] Change ticket status
- [ ] View SLA compliance and breach alerts
- [ ] Access saved replies

### What you CANNOT do

- [ ] Cannot change Google SSO / Slack / email settings (System Manager only)
- [ ] Cannot access Frappe Desk backend

### What to verify

```
1. Log in as lead@helpdesk.localhost
   Expected: Agent desk loads, full ticket queue visible

2. Open any ticket
   Expected: Can see full thread, reply box, internal note option, status dropdown

3. Check Dashboard tab
   Expected: Metrics visible — ticket counts, response times, SLA status

4. Settings > Agents
   Expected: Can view agents, invite new ones

5. Settings > Integrations > Google SSO
   Expected: Fields visible but CANNOT save (read-only for Agent Manager)
   OR: Section not visible at all

6. Assign a ticket to engineer@helpdesk.localhost
   Expected: Ticket appears in engineer's queue

7. Leave an internal note on a ticket
   Expected: Note saved, marked as internal (not visible to customer)
```

---

## Role 4: Agent (DevOps Engineer)

**Login:** engineer@helpdesk.localhost / Test@1234
**Portal:** http://helpdesk.localhost:8000/helpdesk (agent desk)

### What you can do

- [ ] See tickets assigned to them (and unassigned tickets in the queue)
- [ ] Reply to tickets
- [ ] Leave internal notes
- [ ] Change ticket status (Open → In Progress → Resolved)
- [ ] Fill in Root Cause and Internal Notes fields before resolving
- [ ] Use saved replies (canned responses)
- [ ] View their own performance metrics on home dashboard

### What you CANNOT do

- [ ] Cannot see tickets assigned to other agents (only their own + unassigned)
- [ ] Cannot change any settings
- [ ] Cannot invite agents
- [ ] Cannot access Frappe Desk backend

### What to verify

```
1. Log in as engineer@helpdesk.localhost
   Expected: Agent desk loads, only their assigned tickets visible

2. Open an assigned ticket
   Expected: Reply box, internal note option, status dropdown all work

3. Try Settings > Integrations
   Expected: Settings section either hidden or all fields read-only

4. Change ticket status to In Progress
   Expected: Status updates, SLA timer continues

5. Fill Root Cause field and change status to Resolved
   Expected: Ticket marked resolved, customer gets notification (if email configured)

6. Try to open a ticket assigned to another agent
   Expected: Either not visible in list, or read-only

7. Check Home dashboard
   Expected: Their own metrics visible (tickets handled, avg response time)
```

---

## Role 5: Customer (Developer / Any Branch)

**Login:** developer@helpdesk.localhost / Test@1234
**Portal:** http://helpdesk.localhost:8000/helpdesk/tickets (customer portal)

### What you can do

- [ ] Submit new tickets
- [ ] View and track their OWN tickets only
- [ ] Reply to agent responses on their tickets
- [ ] View ticket history and thread
- [ ] Search Knowledge Base articles
- [ ] Reopen a resolved ticket

### What you CANNOT do

- [ ] Cannot see any other user's tickets
- [ ] Cannot access the agent desk (/helpdesk without /tickets)
- [ ] Cannot see internal notes left by agents
- [ ] Cannot see Root Cause or Internal DevOps Notes fields
- [ ] Cannot change any settings

### What to verify

```
1. Log in as developer@helpdesk.localhost
   Expected: Redirected to customer portal (/helpdesk/tickets), NOT agent desk

2. Try to access http://helpdesk.localhost:8000/helpdesk (agent desk directly)
   Expected: Redirected back to customer portal or access denied

3. Click New Ticket
   Expected: Form shows Subject, Description, Type, Priority
   After setup: Also shows Department/Branch, Affected Environment, Project fields

4. Submit ticket:
   Subject: Test ticket from developer
   Type: CI/CD Pipeline
   Priority: High
   Description: Testing the ticketing system
   Expected: Ticket created with unique ID (e.g. HD-0001)

5. View ticket list
   Expected: Only their own ticket visible, not tickets from other users

6. Open the ticket
   Expected: Thread visible, reply box available
   NOT visible: Internal notes, Root Cause, Internal DevOps Notes

7. Search Knowledge Base
   Expected: KB categories visible, articles searchable

8. Try to access Settings
   Expected: No settings option visible in navigation
```

---

## Full End-to-End Flow Test

Run this with 2 browser windows (or incognito + normal):

### Window 1: Customer (developer@helpdesk.localhost)
### Window 2: Agent (engineer@helpdesk.localhost or lead@helpdesk.localhost)

```
Step 1 [Customer]
  Submit new ticket:
  Subject: Production deployment failing
  Type: Deployment Request
  Priority: High
  Department: Engineering
  Environment: Production
  Description: Deploy of v2.1.0 fails with exit code 137

Step 2 [Agent - Window 2]
  Refresh ticket queue
  Expected: New ticket appears with High priority badge

Step 3 [Agent]
  Open ticket → leave internal note:
  "Checking deployment logs. Looks like OOM kill."
  Expected: Note saved as internal (customer cannot see this)

Step 4 [Agent]
  Reply to customer:
  "We've received your request and are investigating the deployment failure."
  Change status to In Progress

Step 5 [Customer - Window 1]
  Refresh ticket
  Expected: Status shows In Progress, agent reply visible
  NOT visible: The internal note from step 3

Step 6 [Agent]
  Fill Root Cause: "Container OOM killed due to memory limit. Increased limit to 2GB."
  Change status to Resolved

Step 7 [Customer]
  Refresh ticket
  Expected: Status shows Resolved
  Can reopen if needed

Step 8 [Agent Manager - lead@helpdesk.localhost]
  Open Dashboard
  Expected: Ticket appears in resolved count, resolution time tracked
```

---

## Quick API Tests (no browser needed)

Test these with curl or browser to verify the backend is working:

```bash
# Health check
curl http://helpdesk.localhost:8000/api/method/ping
# Expected: {"message":"pong"}

# Site config (guest accessible)
curl http://helpdesk.localhost:8000/api/method/helpdesk.api.config.get_config
# Expected: JSON with site name, logo etc.

# Google SSO context (guest accessible)
curl http://helpdesk.localhost:8000/api/method/helpdesk.api.google_sso.get_login_page_context
# Expected: {"message":{"show_google_sso":false}} (false until SSO is configured)

# Initiate Google OAuth (guest accessible, returns error since SSO not configured yet)
curl http://helpdesk.localhost:8000/api/method/helpdesk.api.google_sso.initiate_google_oauth
# Expected: {"message":{"error":"Google SSO is not enabled in HD Settings"}}

# Login as admin and get user info
curl -X POST http://helpdesk.localhost:8000/api/method/login \
  -d "usr=Administrator&pwd=admin"
# Then:
curl http://helpdesk.localhost:8000/api/method/helpdesk.api.auth.get_user \
  -b "sid=<session_id_from_login>"
# Expected: JSON with user info, is_admin:true
```

---

## What to Check After DevOps Setup Script Runs

The setup script auto-creates these — verify they exist:

```
Ticket Types (Settings > Ticket Types):
  ✓ CI/CD Pipeline
  ✓ Server / Infrastructure
  ✓ Database
  ✓ Deployment Request
  ✓ Access & Permissions
  ✓ Environment Setup
  ✓ Security / Credentials
  ✓ Network / VPN
  ✓ Monitoring / Alerting
  ✓ Other

Custom Fields (visible on New Ticket form):
  ✓ Department / Branch (Select dropdown)
  ✓ Affected Environment (Select: Dev/Staging/Prod/All/N/A)
  ✓ Project / Service Name (text)
  ✓ Error Message / Log Snippet (text area)
  ✓ Root Cause (agent-only, NOT visible to customer)
  ✓ Internal DevOps Notes (agent-only, NOT visible to customer)

SLA Policies (Settings > SLA Policies):
  ✓ DevOps SLA exists
  ✓ High: 1h response / 4h resolution
  ✓ Medium: 4h response / 8h resolution
  ✓ Low: 8h response / 72h resolution

Teams (Settings > Teams):
  ✓ DevOps team exists (empty until agents are added)

Knowledge Base (KB icon in nav):
  ✓ CI/CD & Pipelines category
  ✓ Server Access & SSH category
  ✓ Database Operations category
  ✓ Deployment Guides category
  ✓ VPN & Network Access category
  ✓ Common Errors & Fixes category

Saved Replies (Settings > Saved Replies):
  ✓ Ticket Received - Acknowledgement
  ✓ Request for More Information
  ✓ Issue Resolved
  ✓ Deployment Scheduled
  ✓ Access Request - Approved
  ✓ SLA Breach Notification
```

---

## Troubleshooting

**Container not ready yet:**
```bash
docker logs docker-frappe-1 --tail 20
# Wait for: "bench start" output with web/socketio/schedule/worker processes
```

**Site not accessible:**
```bash
# Check if helpdesk.localhost resolves
ping helpdesk.localhost
# If not, add to hosts file:
# Windows: C:\Windows\System32\drivers\etc\hosts
# Add line: 127.0.0.1 helpdesk.localhost
```

**Login not working:**
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost set-admin-password admin"
```

**Run setup script manually (if container already running):**
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost execute helpdesk.setup.devops_setup.run"
```

**Clear cache if UI looks broken:**
```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost clear-cache"
```
