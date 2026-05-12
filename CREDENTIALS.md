# DevOps Ticketing System — Credentials & Post-Setup Guide

After rebuilding the container, these steps require your actual credentials.
Do them in order. Each one takes 5-10 minutes.

Site URL: http://helpdesk.localhost:8000
Admin:    Administrator / admin

---

## Step 1 — Google SSO (CRITICAL — do first)

### 1a. Google Cloud Console

1. Go to https://console.cloud.google.com
2. Create project: "Helpdesk SSO" (or use existing)
3. APIs & Services > OAuth consent screen
   - User Type: **Internal** (restricts to your Google Workspace org only)
   - App name: Company Helpdesk
   - Authorized domain: helpdesk.localhost (or your real domain)
4. Credentials > Create > OAuth 2.0 Client ID
   - Application type: Web application
   - Name: Frappe Helpdesk
   - Authorized redirect URI — use EXACTLY this:
     ```
     http://helpdesk.localhost:8000/api/method/helpdesk.api.google_sso.handle_google_callback
     ```
     (For production replace helpdesk.localhost:8000 with your real domain)
5. Save → copy Client ID and Client Secret

### 1b. Helpdesk Settings UI

1. Log in as Administrator at http://helpdesk.localhost:8000/helpdesk
2. Click Settings (gear icon) > Integrations > Google SSO
3. Fill in:
   - Enable Google SSO: ON
   - Google Client ID: [paste from step 1a]
   - Google Client Secret: [paste from step 1a]
   - Google SSO Allowed Domains: add row → yourcompany.com
4. Click Save

### 1c. Verify

Open incognito browser → http://helpdesk.localhost:8000/login
"Sign in with Google" button should appear.
Log in with a @yourcompany.com account.
Should redirect to /helpdesk (customer portal).

---

## Step 2 — Invite DevOps Agents (CRITICAL — do second)

1. Log in as Administrator
2. Settings > Agents > Invite Agents
3. Add these (use real company emails):

   | Name | Email | Role |
   |---|---|---|
   | DevOps Lead | devops.lead@yourcompany.com | Agent Manager |
   | DevOps Engineer 1 | devops.eng1@yourcompany.com | HD Agent |
   | DevOps Engineer 2 | devops.eng2@yourcompany.com | HD Agent |

4. Each person will receive a welcome email with login instructions.
   They can then log in via Google SSO.

Note: The "DevOps" team was auto-created by the setup script.
After inviting agents, add them to the team:
Settings > Teams > DevOps > add each agent as a member.

---

## Step 3 — Assignment Rules

1. Settings > Assignment Rules
2. Create Rule 1: "High Priority → DevOps Lead"
   - Condition: priority = High
   - Assign to: devops.lead@yourcompany.com
3. Create Rule 2: "DevOps Round Robin"
   - Assign method: Round Robin
   - Assign to team: DevOps
4. Save both rules

---

## Step 4 — Email Notifications (SMTP)

1. Go to http://helpdesk.localhost:8000/app/email-account
2. New Email Account:
   - Email address: devops-tickets@yourcompany.com
   - SMTP server: smtp.gmail.com (or your mail server)
   - SMTP port: 587
   - Use TLS: Yes
   - Password: [App Password from myaccount.google.com/apppasswords]
3. Enable: Use for Outgoing, Default Outgoing
4. Save and test

Then in helpdesk Settings > Email Notifications, enable:
- Acknowledgement email (sent to requester on ticket creation)
- Reply to agents (sent to agent on new assignment)

---

## Step 5 — Slack Webhook

### 5a. Create Slack Incoming Webhook

1. Go to https://api.slack.com/apps
2. Create New App > From Scratch
   - Name: DevOps Ticket Bot
   - Workspace: your company workspace
3. Incoming Webhooks > Activate Incoming Webhooks: ON
4. Add New Webhook to Workspace > select #devops-tickets
5. Copy the Webhook URL (starts with https://hooks.slack.com/services/...)

### 5b. Create Frappe Webhook

1. Go to http://helpdesk.localhost:8000/app/webhook/new-webhook-1
2. Fill in:
   - Webhook DocType: HD Ticket
   - Webhook DocEvent: after_insert
   - Request URL: [paste Slack webhook URL from 5a]
   - Request Method: POST
   - Request Structure: JSON
3. Add Header: Content-Type = application/json
4. Webhook Data (paste this JSON):
   ```json
   {
     "text": "🎫 New Ticket #{{ doc.name }}\n*{{ doc.subject }}*\nRaised by: {{ doc.raised_by }}\nPriority: {{ doc.priority }}\nCategory: {{ doc.ticket_type }}\nEnvironment: {{ doc.custom_environment }}\nDepartment: {{ doc.custom_department }}\n<http://helpdesk.localhost:8000/helpdesk/tickets/{{ doc.name }}|View Ticket>"
   }
   ```
5. Save

### 5c. Verify

Submit a test ticket → message should appear in #devops-tickets within 5 seconds.

---

## Step 6 — SLA Policy Assignment

The "DevOps SLA" policy was auto-created by the setup script.
You need to assign it as the default or link it to the DevOps team:

1. Settings > SLA Policies > DevOps SLA
2. Set as default or configure conditions to apply to DevOps team tickets

---

## What Was Auto-Configured (no action needed)

The setup script already created:

- Ticket types: CI/CD Pipeline, Server / Infrastructure, Database, Deployment Request,
  Access & Permissions, Environment Setup, Security / Credentials, Network / VPN,
  Monitoring / Alerting, Other
- Custom fields on HD Ticket: Department/Branch, Affected Environment, Project/Service Name,
  Error Message/Log Snippet, Root Cause (agent-only), Internal DevOps Notes (agent-only)
- SLA policy: DevOps SLA (High 1h/4h, Medium 4h/8h, Low 8h/72h, Urgent 30min/2h)
- Team: DevOps (empty — add agents after inviting them)
- KB categories: CI/CD & Pipelines, Server Access & SSH, Database Operations,
  Deployment Guides, VPN & Network Access, Common Errors & Fixes
- Saved replies: Ticket Received, Request for More Info, Issue Resolved,
  Deployment Scheduled, Access Request Approved, SLA Breach Notification
- Public signup disabled (only invited users or SSO users can access)

---

## End-to-End Test Sequence

Run this after all steps above are complete.

1. Open http://helpdesk.localhost:8000/helpdesk/tickets in incognito
   Expected: "Sign in with Google" button visible

2. Log in with @yourcompany.com Google account
   Expected: Customer portal loads, empty ticket list

3. Click New Ticket, fill:
   - Subject: CI/CD pipeline broken
   - Type: CI/CD Pipeline
   - Priority: High
   - Department: Engineering
   - Environment: Production
   - Description: Pipeline fails at build step with exit code 1
   Expected: Ticket created with ID HD-0001

4. Check Slack #devops-tickets
   Expected: Notification appears within 5 seconds

5. Check DevOps Lead email
   Expected: [TICKET #HD-0001] New: CI/CD pipeline broken

6. Log in as DevOps Lead at http://helpdesk.localhost:8000/helpdesk
   Expected: Agent desk loads, HD-0001 visible with High priority badge

7. Open ticket > reply to requester > change status to In Progress
   Expected: Requester receives email reply

8. Add root cause > change status to Resolved
   Expected: Requester receives [RESOLVED #HD-0001] email

9. Open Dashboard
   Expected: HD-0001 in Resolved count, resolution time tracked

---

## Rebuild Command

After any code changes, rebuild the container:

```bash
cd docker
docker compose down
docker compose up -d
docker compose logs -f frappe
```

Wait for "bench start" output showing all 4 processes running, then test.
