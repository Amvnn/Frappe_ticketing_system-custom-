# DevOps Ticketing System — Use Case Guide

> Built on Frappe Helpdesk · Self-hosted · Internal use only

---

## The Problem This Solves

| Before | After |
|---|---|
| Verbal queries with no record | Every request is a tracked ticket with a unique ID |
| DevOps room open to anyone | All requests go through the portal — no walk-ins |
| No prioritization | High priority tickets escalated automatically |
| No accountability | SLA timers run on every ticket; breaches are alerted |
| No history or logs | Full audit trail preserved forever |
| No visibility for management | Real-time dashboard with complete metrics |
| Duplicated and lost requests | Nothing gets lost, duplicates are visible |
| Reactive, chaotic workflow | Proactive, structured, measurable DevOps operations |

---

## Is This Platform Aligned With Your Use Case?

- ✅ Internal-only ticketing — no external users, all data on your own server
- ✅ Google Workspace SSO — one-click login, only `@yourcompany.com` accounts
- ✅ Domain-restricted access — block anyone outside your org at the auth layer
- ✅ Structured ticket forms — required fields, categories, priority, environment
- ✅ Auto-assignment via round-robin — fair distribution across DevOps agents
- ✅ SLA enforcement with escalation — per-priority response and resolution deadlines
- ✅ Slack notifications — real-time alerts in `#devops-tickets` on every new ticket
- ✅ Email notifications — requesters get updates at every stage
- ✅ Full audit log — every action timestamped and preserved
- ✅ Knowledge base — document resolved issues, suggest articles before ticket is raised
- ✅ Reporting dashboard — ticket volume, SLA compliance, agent performance, trends
- ✅ Self-hosted via Docker — runs on your company server, no third-party cloud

---

## Who Uses This System

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER ROLES                                 │
├──────────────────────┬──────────────────────────────────────────────┤
│ Administrator        │ Frappe superuser. Full system access.        │
│                      │ Creds: Administrator / admin                 │
├──────────────────────┼──────────────────────────────────────────────┤
│ System Manager       │ DevOps Lead / IT Admin.                      │
│                      │ Configures SSO, SLAs, email, Slack,          │
│                      │ assignment rules, all settings.              │
├──────────────────────┼──────────────────────────────────────────────┤
│ Agent Manager        │ DevOps Lead (day-to-day).                    │
│                      │ Manages agents, teams, views all tickets,    │
│                      │ sees full dashboard and metrics.             │
├──────────────────────┼──────────────────────────────────────────────┤
│ Agent                │ DevOps team member.                          │
│                      │ Works tickets in the agent desk.             │
│                      │ Cannot change settings.                      │
├──────────────────────┼──────────────────────────────────────────────┤
│ Customer             │ Developer / any branch raising a request.    │
│                      │ Customer portal only — submits and tracks    │
│                      │ their own tickets. Auto-assigned on first    │
│                      │ Google SSO login.                            │
└──────────────────────┴──────────────────────────────────────────────┘
```

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                            BROWSER                                   │
│                                                                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐    │
│  │  Agent Desk (Vue SPA)    │    │  Customer Portal (Vue SPA)   │    │
│  │  /helpdesk               │    │  /helpdesk/tickets           │    │
│  │                          │    │                              │    │
│  │  DevOps team works here  │    │  Developers raise tickets    │    │
│  └────────────┬─────────────┘    └──────────────┬───────────────┘    │
└───────────────┼──────────────────────────────────┼────────────────────┘
                │  REST API (frappe.whitelist)      │
                ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FRAPPE BACKEND (Python)                         │
│                                                                      │
│  Authentication ──── Google OAuth2 (SSO) ──── @yourcompany.com only  │
│                                                                      │
│  helpdesk/api/                                                       │
│  ├── auth.py              user info + role flags                     │
│  ├── doc.py               generic list / filter / sort               │
│  ├── ticket.py            ticket assignment                          │
│  ├── agent.py             invite agents                              │
│  ├── dashboard.py         ticket stats                               │
│  ├── agent_home/          agent home widgets + metrics               │
│  ├── knowledge_base.py    KB articles and categories                 │
│  ├── search.py            global search                              │
│  ├── contact.py           contact lookup                             │
│  ├── saved_replies.py     canned reply templates                     │
│  ├── assignment_rule.py   auto-assignment rules                      │
│  ├── config.py            site config (guest)                        │
│  ├── general.py           i18n translations (guest)                  │
│  ├── session.py           user list                                  │
│  ├── slack.py             Slack slash command handler                │
│  ├── google_sso.py        Google OAuth2 SSO flow  ← NEW             │
│  └── settings/                                                       │
│      ├── email.py                 email account setup                │
│      ├── email_notifications.py   notification config                │
│      └── field_dependency.py      field dependency rules             │
│                                                                      │
│  MariaDB ──── Redis (queue/cache) ──── Socket.IO (real-time)         │
│                                                                      │
│  SMTP Email ──── Slack Webhooks                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## User Stories

---

### Story 1 — Developer raises a DevOps ticket

> "As a developer, I want to raise a structured request to the DevOps team so that it is tracked and I can follow its status."

```
Developer opens helpdesk.yourcompany.com
    │
    ├─► [Guest] config.get_config            — load site config
    ├─► [Guest] general.get_translations     — load UI strings
    │
    ├─► Clicks "Sign in with Google"
    │   ├─► google_sso.initiate_google_oauth — generate auth URL + store CSRF state
    │   ├─► → redirected to Google login
    │   └─► google_sso.handle_google_callback
    │           — verify state, exchange code, validate ID token
    │           — check domain: only @yourcompany.com allowed
    │           — auto-create Frappe User with role: Customer (first login)
    │           — establish session → redirect to /helpdesk
    │
    ├─► auth.get_user                        — confirm role = Customer
    │
    ├─► Clicks "New Ticket" and fills form:
    │   Subject, Description, Category (CI/CD / Server / DB / Deployment / Access)
    │   Priority (High / Medium / Low), Environment (Dev / Staging / Prod)
    │   Department, Attachments
    │   └─► frappe.client.insert             — ticket created with unique ID
    │
    ├─► Ticket auto-assigned to a DevOps agent (round-robin assignment rule)
    │   └─► Email sent: "Your ticket #HD-001 has been received"
    │
    └─► Developer tracks status from portal in real time
        └─► doc.get_list_data               — list their own tickets
```

---

### Story 2 — DevOps agent works a ticket

> "As a DevOps agent, I want a clean queue of incoming tickets so I can work through them in priority order without missing anything."

```
DevOps agent logs in → /helpdesk (agent desk)
    │
    ├─► auth.get_user                        — confirm is_agent = true
    ├─► agent_home.get_dashboard             — load home layout
    ├─► agent_home.get_agent_tickets         — my assigned tickets (by period)
    ├─► agent_home.get_pending_tickets       — tickets with SLA risk / breached
    │
    ├─► Opens a ticket
    │   ├─► doc.get_list_data                — full ticket list with filters
    │   ├─► doc.get_filterable_fields        — filter by category, priority, env
    │   ├─► doc.get_quick_filters            — quick filter bar
    │   ├─► search.search                    — find related tickets or KB articles
    │   ├─► contact.search_contacts          — look up the requester
    │   └─► saved_replies.get_rendered_saved_reply  — insert a canned response
    │
    ├─► Replies to requester (response goes to their email + portal)
    │
    ├─► Leaves internal note (visible to DevOps team only)
    │
    ├─► Updates status: Open → In Progress → Resolved
    │   └─► Adds root cause + resolution notes before closing
    │
    └─► Reassigns if needed
        └─► ticket.assign_ticket_to_agent    — assign to self or another agent
            doc.remove_assignments           — remove existing assignment
```

---

### Story 3 — DevOps Lead monitors the team

> "As the DevOps Lead, I want a real-time dashboard so I can see workload, SLA compliance, and agent performance at a glance."

```
DevOps Lead logs in → agent desk
    │
    ├─► auth.get_user                              — confirm is_manager = true
    ├─► dashboard.get_dashboard_data               — aggregate ticket stats
    ├─► agent_home.get_avg_first_response_time     — how fast are we responding?
    ├─► agent_home.get_avg_resolution_time         — how fast are we closing?
    ├─► agent_home.get_avg_time_metrics            — combined time view
    ├─► agent_home.get_recent_feedback             — CSAT scores
    └─► agent_home.get_pending_tickets             — SLA breaches / at-risk tickets

Metrics visible:
    - Total tickets by status (Open / In Progress / Resolved)
    - Tickets by category (CI/CD, Server, DB, Deployment, Access)
    - Tickets by department / branch
    - Average response and resolution times
    - SLA compliance percentage
    - Per-agent performance
    - Weekly and monthly trends
```

---

### Story 4 — Admin sets up the system (one-time)

> "As the System Manager, I want to configure SSO, SLAs, email, Slack, and assignment rules so the system runs automatically."

```
Admin logs in as Administrator
    │
    ├─► Settings > Integrations > Google SSO
    │   ├─► Enable toggle ON
    │   ├─► Enter Google Client ID + Client Secret
    │   ├─► Add allowed domain: yourcompany.com
    │   └─► frappe.client.set_value on HD Settings
    │           — google_sso.get_login_page_context now returns show_google_sso: true
    │           — login page shows "Sign in with Google" button
    │
    ├─► Settings > Integrations > Slack
    │   ├─► Enter Slack Bot Token + Channel (#devops-tickets)
    │   └─► slack.handle_ticket_command wired to /ticket slash command
    │
    ├─► Settings > Email Accounts
    │   └─► settings.email.create_email_account    — configure SMTP outbound
    │       settings.email_notifications.*         — toggle notification types
    │
    ├─► Settings > SLA Policies
    │   Configure per priority:
    │   High   → respond 1h  / resolve 4h
    │   Medium → respond 4h  / resolve 1 business day
    │   Low    → respond 1d  / resolve 3 business days
    │
    ├─► Settings > Assignment Rules
    │   └─► assignment_rule.get_assignment_rules_list
    │       Set up round-robin across DevOps agents
    │       Route High priority → DevOps Lead
    │
    ├─► Settings > Agents — invite DevOps team members
    │   └─► agent.sent_invites                     — create User + HD Agent record
    │
    └─► Settings > Field Dependencies (optional)
        └─► settings.field_dependency.*            — conditional field logic
```

---

### Story 5 — Google SSO login flow (detail)

> "As any company employee, I want to log in with my Google account so I never need a separate password."

```
User clicks "Sign in with Google" on /login
    │
    ├─► [Guest] google_sso.initiate_google_oauth
    │       — reads HD Settings: enable_google_sso, client_id, client_secret
    │       — generates cryptographically random state token
    │       — stores state in frappe.session.data["google_sso_state"]
    │       — builds Google authorization URL with:
    │           client_id, redirect_uri, response_type=code,
    │           scope=openid email profile, access_type=offline, state
    │       — returns URL to browser
    │
    ├─► Browser redirects to Google → user authenticates
    │
    └─► Google redirects to /api/method/helpdesk.api.google_sso.handle_google_callback
            — reads code + state from query params
            — verifies state matches session (CSRF protection), deletes it immediately
            — POSTs to Google token endpoint (10s timeout)
            — decodes and validates ID token:
                aud must match client_id
                exp must be in the future
            — extracts: email, given_name, family_name, picture
            — checks email domain against allowed list (yourcompany.com)
                → domain not allowed: redirect to /login with error
            — provisions Frappe User if first login:
                role: Customer, send_welcome_email: 0
            — calls frappe.local.login_manager.login_as(email)
            — redirects to /helpdesk

Security guarantees:
    - State token is single-use (deleted on consumption)
    - Client secret never appears in logs
    - Domain rejection logs domain only, not full email
    - 10s timeout on all Google API calls
    - Non-2xx responses logged and surfaced as generic error to user
```

---

### Story 6 — Slack notification on new ticket

> "As a DevOps agent, I want a Slack notification in #devops-tickets whenever a new ticket is raised so I don't have to keep checking the portal."

```
New ticket created by developer
    │
    └─► Frappe hook triggers Slack notification
        └─► slack.handle_ticket_command (also handles /ticket slash command)
                — posts to #devops-tickets:
                    Ticket ID, Subject, Priority, Requester, Direct link
                — status updates also posted back to channel
```

---

### Story 7 — Developer self-serves via Knowledge Base

> "As a developer, I want to find answers to common DevOps questions without raising a ticket."

```
Developer types issue subject in search
    │
    ├─► search.search                            — global search across KB + tickets
    │
    └─► System suggests relevant articles before ticket form is submitted
        ├─► [Guest] knowledge_base.get_categories        — browse by category
        ├─► [Guest] knowledge_base.get_category_articles — articles in a category
        ├─► [Guest] knowledge_base.get_article           — read the article
        └─► [Guest] knowledge_base.increment_views       — view count tracked

DevOps Lead documents resolved issues as KB articles:
    ├─► knowledge_base.create_category          — e.g. "CI/CD", "Database", "Access"
    ├─► knowledge_base.move_to_category         — organize articles
    └─► knowledge_base.merge_category           — consolidate duplicate categories
```

---

## Full API Reference

### Auth & Session

| Endpoint | Access | Your use |
|---|---|---|
| `auth.get_user` | Authenticated | Determine if user is agent, manager, or customer on login |
| `auth.get_current_user_email_info` | Agent+ | Load agent's email signature for ticket replies |
| `session.get_users` | Agent+ | List all users for assignment dropdowns |

### Config & i18n

| Endpoint | Access | Your use |
|---|---|---|
| `config.get_config` | Guest | Load site name, logo on portal load |
| `general.get_translations` | Guest | Load UI language strings |

### Tickets & Documents

| Endpoint | Access | Your use |
|---|---|---|
| `doc.get_list_data` | Authenticated | Fetch ticket queue with filters (priority, status, category) |
| `doc.get_filterable_fields` | Authenticated | Build filter UI for ticket list |
| `doc.sort_options` | Authenticated | Sort tickets by SLA, priority, date |
| `doc.get_quick_filters` | Authenticated | Quick filter bar on ticket list |
| `doc.remove_assignments` | Authenticated | Unassign agent from ticket |
| `ticket.assign_ticket_to_agent` | Agent+ | Assign ticket to DevOps agent |

### Agents

| Endpoint | Access | Your use |
|---|---|---|
| `agent.sent_invites` | Agent+ | Onboard DevOps team members as agents |

### Dashboard & Metrics

| Endpoint | Access | Your use |
|---|---|---|
| `dashboard.get_dashboard_data` | Agent+ | Aggregate stats for DevOps Lead overview |
| `agent_home.get_dashboard` | Agent+ | Agent home layout and widgets |
| `agent_home.get_agent_tickets` | Agent+ | My assigned tickets by time period |
| `agent_home.get_avg_first_response_time` | Agent+ | SLA response time tracking |
| `agent_home.get_avg_resolution_time` | Agent+ | SLA resolution time tracking |
| `agent_home.get_avg_time_metrics` | Agent+ | Combined time metrics view |
| `agent_home.get_recent_feedback` | Agent+ | CSAT scores from requesters |
| `agent_home.get_pending_tickets` | Agent+ | Tickets with upcoming or breached SLA |

### Knowledge Base

| Endpoint | Access | Your use |
|---|---|---|
| `knowledge_base.get_categories` | Authenticated | Browse DevOps KB categories |
| `knowledge_base.get_category_articles` | Authenticated | List articles in a category |
| `knowledge_base.get_article` | Guest | Read a KB article |
| `knowledge_base.increment_views` | Guest | Track article usage |
| `knowledge_base.create_category` | Authenticated | Create CI/CD, DB, Access categories |
| `knowledge_base.delete_articles` | Authenticated | Remove outdated articles |
| `knowledge_base.move_to_category` | Authenticated | Reorganize articles |
| `knowledge_base.merge_category` | Authenticated | Consolidate duplicate categories |
| `knowledge_base.get_general_category` | Authenticated | Default category for uncategorized articles |
| `article.get_article_stats` | Authenticated | See which articles are most used |
| `article.search` | Authenticated | Full-text search across KB |

### Search & Contacts

| Endpoint | Access | Your use |
|---|---|---|
| `search.search` | Authenticated | Find related tickets or KB articles |
| `search.get_filter_options` | Authenticated | Filter options for search UI |
| `contact.search_contacts` | Authenticated | Look up the developer who raised a ticket |

### Saved Replies & Onboarding

| Endpoint | Access | Your use |
|---|---|---|
| `saved_replies.get_rendered_saved_reply` | Agent+ | Insert canned responses for common DevOps replies |
| `onboarding.get_first_ticket` | Authenticated | First-run setup helper |
| `onboarding.get_general_category_id` | Authenticated | Default KB category on setup |

### Assignment Rules

| Endpoint | Access | Your use |
|---|---|---|
| `assignment_rule.get_assignment_rules_list` | Authenticated | View and manage round-robin rules |

### Settings

| Endpoint | Access | Your use |
|---|---|---|
| `settings.email.create_email_account` | Admin | Configure SMTP for ticket email notifications |
| `settings.email_notifications.get_data` | Manager+ | View current notification config |
| `settings.email_notifications.update_share_feedback` | Manager+ | Toggle CSAT feedback emails |
| `settings.email_notifications.update_acknowledgement` | Manager+ | Toggle ticket receipt confirmation email |
| `settings.email_notifications.update_reply_to_agents` | Manager+ | Toggle agent reply notifications |
| `settings.email_notifications.update_reply_via_agent` | Manager+ | Toggle reply-via-agent setting |
| `settings.field_dependency.get_field_dependency` | Authenticated | Get conditional field rules |
| `settings.field_dependency.create_update_field_dependency` | Authenticated | Set Environment field to show only for certain categories |

### Integrations

| Endpoint | Access | Your use |
|---|---|---|
| `google_sso.initiate_google_oauth` | Guest | Start Google login from /login page |
| `google_sso.handle_google_callback` | Guest | Complete login, provision user, enforce @yourcompany.com |
| `google_sso.get_login_page_context` | Internal | Show/hide Google button based on SSO toggle |
| `slack.handle_ticket_command` | Guest (Slack) | Post new ticket alerts to #devops-tickets |

---

## Setup Checklist (Your Project Status)

- [x] Infrastructure: self-hosted on company server via Docker
- [x] Core helpdesk platform running and accessible
- [ ] Google SSO — Settings > Integrations > Google SSO → enter Client ID + Secret + domain `yourcompany.com`
- [ ] Custom ticket fields — Department, Environment, Project (via DocType customization)
- [ ] Ticket categories — CI/CD, Server, Database, Deployment, Access
- [ ] SLA rules — High 1h/4h · Medium 4h/1d · Low 1d/3d
- [ ] Assignment rules — round-robin across DevOps agents, High → DevOps Lead
- [ ] Email notifications — SMTP setup in Settings > Email Accounts
- [ ] Slack webhook — Settings > Integrations > Slack → Bot Token + `#devops-tickets`
- [ ] Team onboarding — Settings > Agents > Invite (enter DevOps team emails)
- [ ] Go-live announcement to all branches

---

## Quick Test Credentials

```
URL (Docker):   http://helpdesk.localhost:8000/helpdesk

Admin login:    Administrator / admin

To create test users for each role:
  1. Log in as Administrator
  2. Desk > User List > New User
  3. Set email (must be @yourcompany.com for SSO), first name, password
  4. Assign role: Agent / Agent Manager / System Manager
  5. Log out and log in as that user to verify access

Customer (developer) test:
  - Any @yourcompany.com Google account after SSO is configured
  - Or create a User with no agent roles — they land on the customer portal
```

---

> Built on [Frappe Helpdesk](https://github.com/frappe/helpdesk) · Self-hosted and maintained by the DevOps team
