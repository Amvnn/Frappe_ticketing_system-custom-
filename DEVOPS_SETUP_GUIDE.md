# 🚀 DevOps Ticketing System - Complete Setup & Deployment Guide

This guide will take you from Docker startup to a fully functional DevOps ticketing portal in **5 steps**.

---

## ✅ Status: Your Setup

- ✅ **Docker containers running** (Frappe, MariaDB, Redis)
- ✅ **Helpdesk app installed** (v1.24.1)
- ✅ **Custom fields migration ready**
- ✅ **Ticket types & SLA setup script ready**
- ✅ **Slack integration code ready**

---

## 📋 Step 1: Apply Custom Fields Migration (10 mins)

This adds DevOps-specific fields to the ticket form:
- Department / Branch
- Project Name
- Environment (Dev/Staging/Prod)
- Impact Scope
- Error Code
- Affected Service
- Internal Notes (team only)
- Root Cause
- Resolution Steps
- Prevention Notes

### Run migration:

```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost execute helpdesk.patches.add_devops_custom_fields.execute"
```

**Expected output:**
```
✅ DevOps custom fields added successfully
```

---

## 🏗️ Step 2: Create Ticket Types, SLA Rules & Teams (5 mins)

This script creates:
- **13 ticket types**: CI/CD, Server, Database, Deployment Request, Access, etc.
- **3 SLA rules**: High (1hr response, 4hr resolution), Medium (4hr, 1 day), Low (1 day, 3 days)
- **Assignment rules**: Round-robin distribution
- **DevOps team**: Ready for members

### Run setup:

```bash
docker exec docker-frappe-1 bash -c "cd /home/frappe/frappe-bench && bench --site helpdesk.localhost execute helpdesk.setup.devops_setup.execute"
```

**Expected output:**
```
✅ Setting up DevOps Ticketing System
✅ Created team: DevOps
✅ Created ticket type: CI/CD Pipeline
✅ Created ticket type: Server / Infrastructure
... (11 more types)
✅ Created SLA: High Priority 24/7
✅ Created SLA: Medium Priority Business Hours
✅ Created SLA: Low Priority
✅ Assignment rules configured
✅ Email templates defined
✅ DevOps setup complete!
```

---

## 🔑 Step 3: Configure Global Settings (15 mins)

### Access Settings:

```
http://helpdesk.localhost:8000/app/hd-settings
```

### Login:
- **Username:** Administrator
- **Password:** admin

### Configure:

1. **Brand Settings**
   - Company Name: Your Company
   - Logo: Upload your logo
   - Primary Color: Your brand color

2. **Working Hours** (for SLA pausing outside business hours)
   - Working Days: Monday - Friday
   - Start Time: 09:00
   - End Time: 18:00

3. **Holidays** (if applicable)
   - Click "Service Holiday List"
   - Add public holidays to prevent SLA clock from running

---

## 📧 Step 4: Set Up Email Notifications (15 mins)

This ensures your team gets notified when tickets are created, assigned, or SLA is breaching.

### Step 4a: Configure Email Account

```
http://helpdesk.localhost:8000/app/email-account
```

1. Click "+ New Email Account"
2. **Email Address:** your-notification@yourcompany.com
3. **Email Provider:** SMTP / Your Provider
4. **SMTP Server:** mail.yourcompany.com (or your email host)
5. **SMTP Port:** 587
6. **Username & Password:** Your email credentials
7. **Check:** "Enable Incoming" if you want email-to-ticket feature
8. Save and test

### Step 4b: Create Notification Rules

```
http://helpdesk.localhost:8000/app/hd-notification
```

Create these notifications (click "+ New"):

#### Notification 1: New Ticket Alert
- **Name:** New Ticket Alert
- **Trigger:** On Create
- **Recipients:** All team members
- **Subject:** `[TICKET #{{ doc.name }}] 🎫 New: {{ doc.subject }}`
- **Template:**
```
Ticket #{{ doc.name }} has been created.

🔹 Subject: {{ doc.subject }}
🔹 Raised By: {{ doc.raised_by_name }}
🔹 Priority: {{ doc.priority }}
🔹 Category: {{ doc.ticket_type }}
🔹 Environment: {{ doc.environment or 'N/A' }}

👉 Open in Helpdesk: https://helpdesk.yourcompany.com/app/hd-ticket/{{ doc.name }}
```

#### Notification 2: Ticket Assigned to You
- **Name:** Ticket Assigned to Agent
- **Trigger:** On Update (assigned_to changes)
- **Recipients:** Assigned To
- **Subject:** `[ASSIGNED] 👤 {{ doc.name }} {{ doc.subject }}`
- **Template:**
```
This ticket has been assigned to you.

🔹 Ticket: #{{ doc.name }}
🔹 Subject: {{ doc.subject }}
🔹 Priority: {{ doc.priority }}
🔹 SLA Response Time: {{ doc.sla_response_time or 'N/A' }}

👉 Take Action: https://helpdesk.yourcompany.com/app/hd-ticket/{{ doc.name }}
```

#### Notification 3: SLA Breach Warning
- **Name:** SLA Breach Alert
- **Trigger:** Scheduled (hourly) — when SLA Status becomes "Breached"
- **Recipients:** DevOps Lead (or Agent Manager)
- **Subject:** `🚨 [SLA BREACH] {{ doc.name }} {{ doc.subject }}`
- **Template:**
```
⚠️ SLA BREACH ALERT

Ticket #{{ doc.name }} has breached its SLA.

🔹 Subject: {{ doc.subject }}
🔹 Created: {{ doc.creation }}
🔹 SLA Status: BREACHED
🔹 Assigned To: {{ doc.assigned_to_name }}

👉 Immediate Action: https://helpdesk.yourcompany.com/app/hd-ticket/{{ doc.name }}
```

---

## 👥 Step 5: Add DevOps Team Members (10 mins)

### Create users for each team member:

```
http://helpdesk.localhost:8000/app/user
```

For each team member, create a **User** (if not already existing):
- **Email:** firstname.lastname@yourcompany.com
- **First Name:** Their first name
- **Roles:** Add "Agent" role

### Add to DevOps Team:

```
http://helpdesk.localhost:8000/app/hd-team
```

1. Click on "DevOps" team
2. Scroll to "Team Members" table
3. Add each user: click "+ Add Row"
4. Select user email → they're now part of the team
5. Save

---

## 🔐 Step 6: Configure SSO Login (Optional but Recommended)

### Option A: Google Workspace (if your company uses Google)

```
http://helpdesk.localhost:8000/app/social-login-key
```

1. **Create Social Login Key**
   - Provider: Google
   - Client ID: (from Google Cloud Console)
   - Secret: (from Google Cloud Console)
   - **Allowed Domains:** yourcompany.com (only your company can log in)

2. **Steps to get Google credentials:**
   - Go to https://console.cloud.google.com
   - Create a new project
   - Enable "Google+ API"
   - Create OAuth 2.0 credentials (Web Application)
   - Authorized redirect URIs: `https://helpdesk.yourcompany.com/api/method/frappe.integrations.oauth2_logins.login`

### Option B: LDAP / Active Directory (if on-premise)

```
http://helpdesk.localhost:8000/app/ldap-settings
```

- **LDAP Server:** ldap://your-ad-server
- **Base DN:** dc=yourcompany,dc=com
- **Bind DN:** cn=admin,dc=yourcompany,dc=com
- **Bind Password:** Admin password

---

## 💬 Step 7: Slack Integration (Optional - 20 mins)

### Part A: Frappe → Slack Notifications

This sends automatic Slack notifications when tickets are created.

#### Create Slack Webhook:

1. Go to https://api.slack.com/apps
2. Click "Create New App" → From scratch
3. **App Name:** Frappe Helpdesk
4. **Select Workspace:** Your company workspace
5. Go to **Incoming Webhooks** → Enable
6. Click "Add New Webhook to Workspace"
7. Select channel: **#devops-tickets** (create if needed)
8. **Copy the webhook URL:** `https://hooks.slack.com/services/T.../B.../...`

#### Add webhook to Frappe:

```
http://helpdesk.localhost:8000/app/webhook
```

Create a new webhook:
- **DocType:** HD Ticket
- **Event:** On Create (After Insert)
- **URL:** Paste your Slack webhook URL
- **Method:** POST
- **Body:**
```json
{
  "text": "🎫 New Ticket",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Ticket #{{ doc.name }}*: {{ doc.subject }}\nRaised by: {{ doc.raised_by }}\nPriority: {{ doc.priority }}\nCategory: {{ doc.ticket_type }}"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "Open Ticket"
          },
          "url": "https://helpdesk.yourcompany.com/app/hd-ticket/{{ doc.name }}"
        }
      ]
    }
  ]
}
```

### Part B: Slack `/ticket` Command (Advanced)

This allows DevOps to create tickets directly from Slack using `/ticket [description]`.

#### Create Slack App (if not done above):

1. Go to https://api.slack.com/apps → Your app
2. Go to **Slash Commands** → Create New Command
3. **Command:** `/ticket`
4. **Request URL:** `https://helpdesk.yourcompany.com/api/method/helpdesk.api.slack.handle_ticket_command`
5. **Short Description:** "Create a support ticket"
6. Save

#### Set up OAuth Token:

1. Go to **OAuth & Permissions**
2. Add these **Bot Token Scopes:**
   - `chat:write`
   - `commands`
   - `users:read`
3. **Install to Workspace** (or reinstall)
4. Copy **Bot User OAuth Token:** `xoxb-...`

#### Add token to Frappe config:

```
http://helpdesk.localhost:8000/app/system-settings
```

Add these **Custom Settings** (JSON):
```json
{
  "slack_bot_token": "xoxb-your-token-here",
  "slack_signing_secret": "your-signing-secret-here"
}
```

The signing secret is in your Slack app under **Basic Information** → **Signing Secret**.

#### Test it:

In Slack, type: `/ticket Database connection pool exhausted on prod`

✅ You should get an instant confirmation and a ticket should appear in Helpdesk!

---

## 🎯 Step 8: Train Your Team (1 hour)

### Agents (DevOps team) should know:

1. **Access the app:** `https://helpdesk.yourcompany.com/helpdesk`
2. **Dashboard:** See all open tickets, filter by priority/status
3. **Assign workflow:** Ticket → Assign to Self → Respond → Change Status → Resolve
4. **Use saved views:** My Open Tickets, High Priority, SLA At Risk
5. **Keyboard shortcuts:** Press `?` for help

### Requesters (developers/branches) should know:

1. **Access the portal:** `https://helpdesk.yourcompany.com/support`
2. **Create ticket:** Click "New Ticket" → fill form with all details
3. **Track progress:** Can see assigned agent, SLA countdown, status
4. **Communicate:** Reply in thread or via email

---

## 📊 Step 9: Monitor & Report (Ongoing)

### Daily:
- Check **Agent Dashboard** for SLA breaches
- Review **All Unassigned** queue

### Weekly:
- Export **Team Performance Report**
  ```
  Reports → Ticket Summary
  Filter: Last 7 days
  Metrics: Avg response time, resolution time, SLA compliance
  ```

### Monthly:
- Review **Most Common Issues** (ticket types)
- Identify **Process Improvements** (reducing ticket volume)

---

## 🔧 Troubleshooting

### Tickets not sending emails?
- Go to **Settings → Email Account**
- Click "Send Test Email"
- Check **Frappe Logs** for SMTP errors

### Team members can't see tickets?
- Verify they're added to "DevOps" team in **Settings → Teams**
- Verify they have "Agent" role in **Users**
- Check **Permissions** on HD Ticket

### SLA not updating?
- Check scheduler job running: **Settings → Scheduled Jobs**
- Verify "Update SLA Status" job is enabled and running

### Slack not connecting?
- Verify bot token in custom settings
- Check webhook URL is correct
- Review Slack app logs at https://api.slack.com/apps

---

## 📱 Mobile Access

The system is fully responsive and works on any device (phone, tablet, laptop).

**Mobile-friendly features:**
- Optimized touch interface
- Can update tickets on the go
- Push-like notifications when assigned
- Works offline (PWA)

Just open `https://helpdesk.yourcompany.com/helpdesk` on your phone!

---

## 🚀 Production Deployment (Beyond Docker)

When ready to go production on a real server:

1. **Use managed hosting:** [Frappe Cloud](https://frappecloud.com) (easiest)
   OR
2. **Self-host on a VPS:**
   ```bash
   wget https://frappe.io/easy-install.py
   python3 ./easy-install.py deploy \
       --project=helpdesk_prod \
       --email=your_email@company.com \
       --image=ghcr.io/frappe/helpdesk \
       --version=stable \
       --app=helpdesk \
       --sitename=helpdesk.yourcompany.com
   ```

3. **Configure DNS:** Point your domain to your server
4. **Enable HTTPS:** Auto via Let's Encrypt (recommended)
5. **Backup:** Enable daily backups to secure storage

---

## 📚 Architecture Summary

```
┌─────────────────────────────────────┐
│   Your Company (Developers)          │
│  Portal: /support                    │
│  → Create tickets                    │
│  → Track SLA                         │
└─────────────────────────────────────┘
           ↓ HTTP/HTTPS ↓
┌─────────────────────────────────────┐
│   FRAPPE HELPDESK (Your Docker)      │
│  Agent Panel: /helpdesk              │
│  - Ticket management                 │
│  - Real-time collaboration           │
│  - Assignment & SLA tracking         │
└─────────────────────────────────────┘
           ↓ Integrations ↓
┌─────────────────────────────────────┐
│ Email, Slack, SSO, Webhooks          │
└─────────────────────────────────────┘
           ↓ Data ↓
┌─────────────────────────────────────┐
│ MariaDB (tickets, users, history)    │
│ Redis (cache, real-time)             │
└─────────────────────────────────────┘
```

---

## ✅ Checklist: Ready to Launch?

- [ ] Custom fields applied (`/app/hd-ticket` shows new fields)
- [ ] Ticket types created (13 types visible in form)
- [ ] SLA rules configured (3 rules visible in settings)
- [ ] Team created with members
- [ ] Email account configured and tested
- [ ] Notifications created (at least 2)
- [ ] SSO login working (optional but recommended)
- [ ] Slack notifications working (optional)
- [ ] Team trained and comfortable
- [ ] Requesters can access `/support` portal
- [ ] First test ticket created and workflow verified

---

## 🎉 You're Done!

Your DevOps ticketing system is now live. Start using it immediately:

- **Agents:** `https://helpdesk.yourcompany.com/helpdesk`
- **Requesters:** `https://helpdesk.yourcompany.com/support`
- **Settings:** `https://helpdesk.yourcompany.com/app/hd-settings`

**Questions?** Check [Frappe Helpdesk Docs](https://docs.frappe.io/helpdesk) or [Frappe Forum](https://discuss.frappe.io/c/frappehelpdesk)

---

*Last updated: May 2026*
