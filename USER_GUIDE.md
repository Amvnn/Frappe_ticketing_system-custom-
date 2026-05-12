# 🎫 DevOps Ticketing System - Complete User Guide

**For:** DevOps Team | **Version:** 1.0 | **Last Updated:** May 12, 2026

---

## 📖 Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Understanding Tickets](#understanding-tickets)
3. [Creating & Managing Tickets](#creating--managing-tickets)
4. [Ticket Workflow](#ticket-workflow)
5. [Team Collaboration](#team-collaboration)
6. [Searching & Organizing](#searching--organizing)
7. [SLA & Priority Management](#sla--priority-management)
8. [Real-World Scenarios](#real-world-scenarios)
9. [Tips & Best Practices](#tips--best-practices)
10. [FAQ & Troubleshooting](#faq--troubleshooting)

---

## Quick Start

### Step 1: Login (30 seconds)

Open your browser and go to:
```
http://localhost:8000/helpdesk
```

**First time setup?**
- Username: `Administrator`
- Password: `admin`

**After setup, use your own account:**
- Your team lead will create accounts for each team member
- You'll receive your login credentials

### Step 2: View Your Dashboard (1 minute)

After login, you'll see your **Dashboard** with:
- **📊 My Tickets** - All tickets assigned to you
- **🔴 Urgent** - High priority tickets needing immediate attention
- **📈 Statistics** - Your ticket metrics
- **⏰ SLA Status** - Which tickets are at risk

### Step 3: Create Your First Ticket (2 minutes)

Click **"New Ticket"** button at the top

Fill in:
- **Subject:** Brief description
- **Description:** Detailed information
- **Priority:** High/Medium/Low (affects SLA)
- **Type:** Select from 13 predefined types

Click **"Save"** → Your ticket is created!

---

## Understanding Tickets

### What is a Ticket?

A **Ticket** is a documented issue or task that needs to be tracked from start to finish. Each ticket has:

- **Unique ID** - Auto-generated identifier (e.g., `HD-2345`)
- **Status** - Current stage (New → In Progress → Resolved → Closed)
- **Priority** - Urgency level (High/Medium/Low)
- **Type** - Category of the ticket
- **Assigned To** - Team member responsible
- **Timeline** - Creation date, resolution date, SLA times

### Ticket Types (13 Categories)

```
1. CI/CD Pipeline          → Issues with deployment pipelines
2. Server/Infrastructure   → Server or infra problems
3. Database               → Database issues or maintenance
4. Deployment Request     → Deployment authorization needed
5. Access & Permissions   → User access issues
6. Environment Setup      → Dev/Staging/Prod setup
7. Security/Credentials   → Security or credential issues
8. Network/VPN            → Network connectivity issues
9. Monitoring & Alerts    → Monitoring system problems
10. Performance Issue      → Application slowness
11. Data Migration         → Data migration tasks
12. Backup & Recovery      → Backup/restore operations
13. Other                  → Anything else
```

### Ticket Status Lifecycle

```
┌─────────┐     ┌────────────────┐     ┌──────────┐     ┌────────┐
│   NEW   │  →  │  IN PROGRESS   │  →  │ RESOLVED │  →  │ CLOSED │
└─────────┘     └────────────────┘     └──────────┘     └────────┘

NEW:          Just created, waiting for assignment
IN PROGRESS:  Assigned and being worked on
RESOLVED:     Work complete, waiting for customer confirmation
CLOSED:       Customer confirmed, ticket archived
```

### Priority Levels & SLA

```
HIGH PRIORITY
├─ Response Time: 1 hour
├─ Resolution Time: 4 hours
└─ Available: 24/7

MEDIUM PRIORITY
├─ Response Time: 4 hours
├─ Resolution Time: 24 hours (1 business day)
└─ Available: Business hours only (9 AM - 6 PM)

LOW PRIORITY
├─ Response Time: 24 hours (1 business day)
├─ Resolution Time: 72 hours (3 business days)
└─ Available: Business hours only (9 AM - 6 PM)
```

---

## Creating & Managing Tickets

### How to Create a Ticket

#### Option 1: From Web Interface (Recommended for everyone)

1. Go to **http://localhost:8000/helpdesk**
2. Click **"New Ticket"** button (top right)
3. Fill in the form:

```
TICKET FORM
───────────────────────────────────────────

Subject *                 [_____ Brief title _____]

Description *             [___ Detailed description ___]
                          [Include what happened, when, impact]

Type *                    [Select from dropdown ▼]
                          - CI/CD Pipeline
                          - Server/Infrastructure
                          - Database
                          - (etc.)

Priority                  [Select level ▼]
                          ○ High   (1hr response, 4hr resolution)
                          ○ Medium (4hr response, 1 day resolution)
                          ○ Low    (1 day response, 3 day resolution)
                          Default: Medium

Department                [Engineering / Infrastructure / etc.]

Project Name              [Which project does this affect?]

Environment               [Development / Staging / Production]

Impact Scope              [Single User / Team / Service-Wide]

───────────────────────────────────────────
[SAVE]  [CLEAR]
```

4. Click **SAVE** → Your ticket is created with ID like `HD-2345`
5. You'll see:
   - Ticket ID
   - Status badge (NEW)
   - Confirmation message

#### Option 2: From Slack (If configured)

**DevOps can use Slack to create tickets:**

```
In Slack, use the slash command:
/ticket Create ticket for database backup failed

The bot will create a ticket and reply with a link
```

### Example Tickets

#### Example 1: Server Down (High Priority)

```
Subject: Production API Server - HTTP 503 Errors

Description:
API server (prod-api-01) started returning HTTP 503 errors at 2:15 PM
Users unable to login. Error log shows "Connection timeout to database"
Last deployment was 1 hour ago

Impact: All users unable to access the platform
Affected Service: prod-api-01

Type: Server/Infrastructure
Priority: HIGH (requires 1 hr response)
Environment: Production
Impact Scope: Company-Wide
```

#### Example 2: Pipeline Build Failure (Medium Priority)

```
Subject: CI Pipeline failing for microservices repo

Description:
Pipeline job "build-staging" failed 3 times today
Error: "npm test exiting with code 1"
Tests are failing in UserService.test.js

This is blocking staging deployments for the day

Type: CI/CD Pipeline
Priority: MEDIUM
Environment: Staging
Project Name: Microservices
```

#### Example 3: Database Maintenance (Low Priority)

```
Subject: Monthly database optimization needed

Description:
Need to run monthly maintenance on prod-mysql-01:
- Table optimization
- Index rebuild
- Statistics update

Can be done anytime in next 3 days
Current database size: 450 GB

Type: Database
Priority: LOW
Environment: Production
Department: Infrastructure
```

### Viewing Your Tickets

**Dashboard View:**
- Go to **http://localhost:8000/helpdesk**
- See all your assigned tickets
- Shows status, priority, age, SLA status

**List View:**
- Go to **http://localhost:8000/app/hd-ticket**
- See ALL tickets (created by anyone)
- Can filter and search

**Details View:**
- Click any ticket to see full details
- See all comments and history
- Can update status, priority, notes

---

## Ticket Workflow

### The Journey of a Ticket

```
Day 1 - Monday 10:00 AM
┌─────────────────────────────────────────┐
│ TICKET CREATED                          │
│ Subject: Database replication lag       │
│ Status: NEW                             │
│ Priority: MEDIUM                        │
│ SLA Timer Started: 4 hours for response │
└─────────────────────────────────────────┘
                    ↓
Day 1 - Monday 11:30 AM (1.5 hrs later)
┌─────────────────────────────────────────┐
│ TICKET ASSIGNED                         │
│ Assigned To: Raj Kumar                  │
│ Status: IN PROGRESS                     │
│ Raj commented: "Investigating now..."   │
│ SLA Timer: 2.5 hours remaining          │
└─────────────────────────────────────────┘
                    ↓
Day 1 - Monday 2:15 PM (4.25 hrs later)
┌─────────────────────────────────────────┐
│ TICKET UPDATED                          │
│ Raj added: "Found issue in binlog"      │
│ Status: IN PROGRESS                     │
│ Raj started work on fix                 │
└─────────────────────────────────────────┘
                    ↓
Day 1 - Monday 3:45 PM (5.75 hrs later)
┌─────────────────────────────────────────┐
│ TICKET RESOLVED                         │
│ Status: RESOLVED                        │
│ Raj added: "Fixed binlog corruption"    │
│ Resolution Time: 5 hours 45 minutes     │
│ SLA Met: ✅ (within 24 hour resolution) │
└─────────────────────────────────────────┘
                    ↓
Day 1 - Monday 4:00 PM
┌─────────────────────────────────────────┐
│ REQUESTER CONFIRMS                      │
│ Customer replied: "Confirmed fixed!"    │
│ Status: CLOSED                          │
│ Ticket archived and logged              │
└─────────────────────────────────────────┘
```

### Your Role at Each Stage

| Stage | Your Action | What to Do |
|-------|------------|-----------|
| **NEW** | Receive ticket | Review if assigned to you |
| **NEW** | Review details | Understand the problem |
| **NEW** | Ask questions | Add comments if need clarification |
| **IN PROGRESS** | Work on issue | Update status, add progress notes |
| **IN PROGRESS** | Post updates | Comment frequently so others know status |
| **RESOLVED** | Confirm fix | Add resolution notes |
| **RESOLVED** | Wait for confirmation | Customer may ask for more info |
| **CLOSED** | Archive | Ticket moves to history for audit |

---

## Team Collaboration

### Adding Comments

**How to comment on a ticket:**

1. Open the ticket
2. Scroll to **Comments** section
3. Type your update
4. Click **Post Comment**

**When to comment:**
- Starting work: "Starting investigation now..."
- Progress updates: "Found issue in XYZ config, applying fix..."
- Need help: "@MentionName Can you review this error?"
- Done: "Confirmed working, SLA met ✅"

### Mentioning Team Members

**Use @ symbol to notify someone:**

```
@RajKumar Can you verify this works in staging?
@TeamLead Please review the root cause analysis
@DatabaseTeam Are these changes safe to deploy?
```

→ They get **instant notification** via email/dashboard

### Assigning Tickets

**How to reassign a ticket:**

1. Open the ticket
2. Click the **"Assigned To"** field
3. Type team member name or click dropdown
4. Select the person
5. Click **Save**

**When to reassign:**
- Someone is more experienced with this issue
- The assigned person is unavailable
- Moving to next team in workflow (Dev → QA → DevOps)

### Adding Internal Notes

**For team eyes only (not visible to customer):**

1. Open ticket
2. Find **Internal Notes** field
3. Type confidential notes
4. Save

**Examples:**
- "This customer always panics, be patient"
- "Raj mentioned similar issue last week, see ticket HD-1234"
- "This is billing fraud, alert management"

---

## Searching & Organizing

### Finding Tickets You Need

#### Search by Status

```
Go to: http://localhost:8000/app/hd-ticket

Click Filter button, select:
Status = "In Progress"

Shows: All tickets you're working on right now
```

#### Search by Priority

```
Filter: Priority = "High"

Shows: All high-priority tickets (1 hour SLA)
```

#### Search by Type

```
Filter: Type = "CI/CD Pipeline"

Shows: Only pipeline-related tickets
```

#### Search by Created Date

```
Filter: Creation Date = "This Week"

Shows: All tickets from past 7 days
Example uses: "This Week", "This Month", "Last 30 Days"
```

#### Advanced Search

**Find all Production issues from last week:**

```
Filter Criteria:
  AND Environment = "Production"
  AND Creation Date = "Last Week"
  AND Status ≠ "Closed"

Result: Shows open production issues from past week
```

### Useful Filters for DevOps

```
Filter Name              | Filter Criteria | Use Case
─────────────────────────────────────────────────────────
My Open Tickets         | Assigned To = Me, Status ≠ Closed
                        | → See your work queue

SLA at Risk             | SLA Status = "At Risk"
                        | → Tickets nearing SLA deadline

Production Issues       | Environment = Production, Status ≠ Closed
                        | → All open production problems

Today's Issues          | Creation Date = Today
                        | → New tickets arrived today

Unassigned              | Assigned To = Empty
                        | → Tickets waiting for assignment

Database Tasks          | Type = Database
                        | → All database-related work
```

### Creating Saved Filters

**To save a filter for quick access:**

1. Apply your filters (Status = In Progress, Priority = High, etc.)
2. Click **Save Filter** button
3. Name it: "My High Priority Work"
4. Click **Save**

→ Now appears in left sidebar for quick access!

---

## SLA & Priority Management

### Understanding SLA (Service Level Agreement)

SLA defines how quickly we must respond/resolve based on priority:

```
SCENARIO 1: Database Down (HIGH)
├─ Created: Monday 9:00 AM
├─ SLA: 1 hour response, 4 hour resolution
├─ Response Due: 10:00 AM (by then must assign)
├─ Resolution Due: 1:00 PM (by then must resolve)
└─ Status: 🔴 URGENT if still open at 1:00 PM

SCENARIO 2: Performance Slow (MEDIUM)
├─ Created: Monday 9:00 AM
├─ SLA: 4 hour response, 24 hour resolution
├─ Response Due: 1:00 PM
├─ Resolution Due: Tuesday 9:00 AM
└─ Status: ⚠️ Warning if working past 1:00 PM

SCENARIO 3: Feature Request (LOW)
├─ Created: Monday 9:00 AM
├─ SLA: 24 hour response, 72 hour resolution
├─ Response Due: Tuesday 9:00 AM
├─ Resolution Due: Thursday 9:00 AM
└─ Status: 👍 Relaxed, you have time
```

### SLA Status Indicators

```
🟢 GREEN / ✅ ON TRACK
   → You're ahead of schedule
   → No action needed

🟡 YELLOW / ⚠️ AT RISK
   → Less than 25% time remaining
   → Start wrapping up

🔴 RED / 🚨 OVERDUE
   → SLA time has passed
   → URGENT - escalate immediately
   → Alert your manager
```

### How to Meet SLA

**For HIGH Priority (1 hr / 4 hr):**
```
9:00 AM - Ticket created
9:05 AM - Assign ticket
9:30 AM - Start working
12:30 PM - Have solution
1:00 PM - Document resolution ✅ Within 4 hr SLA
```

**For MEDIUM Priority (4 hr / 24 hr):**
```
9:00 AM - Ticket created
12:00 PM - Acknowledge (within 3 hr response window)
2:00 PM - Start working
Next day 9:00 AM - Have resolution ✅ Within 24 hr SLA
```

---

## Real-World Scenarios

### Scenario 1: Production Database Down

**Step 1: Create Ticket**
```
Subject: CRITICAL - Production DB Connection Timeout

Description:
Production API unable to connect to MySQL database.
All users getting 503 errors. Started at 2:15 PM.
Error: "Timeout waiting for replica connection"

Ticket created: 2:16 PM
```

**Step 2: System Auto-Assigns**
```
SLA: HIGH (1 hr response required)
Alert: Raj Kumar gets notification immediately
```

**Step 3: First Response**
```
2:20 PM - Raj acknowledges: "I'm investigating"
Raj updates status: "IN PROGRESS"
```

**Step 4: Working on Fix**
```
2:35 PM - Raj comments: "Found connection timeout in replica"
2:50 PM - Raj comments: "Restarting MySQL replication..."
3:05 PM - Raj comments: "Connections restored ✅"
```

**Step 5: Resolution**
```
3:10 PM - Status changed to RESOLVED
Raj adds: "Root cause: Replica lag exceeded max_allowed_lag"
SLA MET: ✅ (Resolved in 54 minutes, 4 hour SLA)
```

**Step 6: Close**
```
3:15 PM - Engineering team confirms working
Raj clicks CLOSE
Ticket archived in history for audit
```

### Scenario 2: CI Pipeline Build Failing

**Step 1: Ticket Created**
```
Subject: CI Pipeline Build Failing - microservices repo

Description:
Build failing on "npm test" step for 3 commits in a row.
Error in UserService.test.js line 245
Blocking: Can't deploy to staging

Priority: MEDIUM (4 hr response)
Created: 10:00 AM
```

**Step 2: Investigation**
```
10:30 AM - Priya (QA) comments: "Tests worked yesterday"
10:45 AM - Priya: "Found issue - test data setup failed"
11:00 AM - Priya: "Fixed setup, tests pass now ✅"
```

**Step 3: Verification**
```
11:15 AM - Pipeline re-runs
11:30 AM - Pipeline SUCCEEDS
Priya comments: "Build passing, ready to merge"
```

**Step 4: Close**
```
11:45 AM - Dev team confirms merged
Priya updates: Status = RESOLVED
SLA MET: ✅ (1 hr 45 min, within 4 hour window)
```

### Scenario 3: Employee Access Request

**Step 1: Request Created**
```
Subject: New Contractor Needs Access to Staging DB

Description:
New contractor starting Monday needs:
- VPN access
- Staging DB readonly access
- GitHub access to staging branch

Type: Access & Permissions
Priority: MEDIUM
Created: Friday 4:00 PM
```

**Step 2: Assignment**
```
System auto-assigns to: Access Team Lead
Note: Low priority, can be done Monday morning
```

**Step 3: Processing**
```
Monday 9:00 AM - Team lead starts processing
Monday 10:00 AM - Sends contractor:
  - VPN credentials
  - DB connection string (read-only)
  - GitHub invitation
  - Welcome packet
```

**Step 4: Verification**
```
Monday 11:00 AM - Contractor confirms all access working
Monday 11:15 AM - Team lead updates: RESOLVED
```

**Step 5: Close**
```
Monday 11:30 AM - Contractor confirms ready to start
Team lead clicks: CLOSE
Record saved for contractor onboarding audit trail
```

---

## Tips & Best Practices

### ✅ Do This

#### 1. Create Detailed Tickets
```
❌ BAD:  "Server down"
✅ GOOD: "Production API Server prod-api-01 returning HTTP 503 errors since 2:15 PM. 
         Error in logs: 'Connection timeout to database'. 
         Last deployment 1 hour ago. Affecting all users."
```

#### 2. Add Progress Comments
```
❌ BAD:  [Silent, no updates]
✅ GOOD: "2:00 PM - Starting investigation"
         "2:30 PM - Found root cause in config"
         "3:00 PM - Applied fix, testing..."
         "3:15 PM - Verified working ✅"
```

#### 3. Update Status
```
❌ BAD:  Leave as "NEW" while working
✅ GOOD: Change to "IN PROGRESS" when you start
         Change to "RESOLVED" when done
         System automatically tracks SLA based on status changes
```

#### 4. Use Correct Type & Priority
```
❌ BAD:  Everything as "Other" type, all "High" priority
✅ GOOD: Categorize correctly:
         - Security issue → "Security/Credentials"
         - Build fail → "CI/CD Pipeline"
         - User can't login → "Access & Permissions"
         
         Prioritize correctly:
         - Production down → HIGH (1 hr SLA)
         - Staging issue → MEDIUM (4 hr SLA)
         - Nice to have → LOW (24 hr SLA)
```

#### 5. Document for Others
```
❌ BAD:  "Fixed it"
✅ GOOD: "Root cause: Config file had old IP address for
         database server. Updated to new IP 10.20.30.1.
         Verified in prod-mysql logs that connections succeeded."
```

#### 6. Mention People When You Need Help
```
❌ BAD:  Wait silently
✅ GOOD: "@RajKumar Can you review? Not sure if safe to deploy"
         "@DatabaseTeam Is this the correct backup procedure?"
```

---

### ❌ Don't Do This

#### 1. Don't Leave Tickets Unassigned
```
❌ WRONG: Ticket sits "NEW" for 3 hours
✅ RIGHT: Assign yourself or request assignment within 1 hour
```

#### 2. Don't Ignore SLA Warnings
```
❌ WRONG: Continue working slowly when SLA turns yellow
✅ RIGHT: Escalate or request help when SLA at risk
```

#### 3. Don't Create Duplicate Tickets
```
❌ WRONG: "Database down #1", "Database down #2", "DB Issue"
✅ RIGHT: Search first, comment on existing ticket if already reported
```

#### 4. Don't Use Tickets as Chat
```
❌ WRONG: Dozens of comments like "ok", "still working", "gimme sec"
✅ RIGHT: Meaningful updates: "Found issue", "Applied fix", "Testing"
```

#### 5. Don't Change Priority Randomly
```
❌ WRONG: Mark everything HIGH to get attention
✅ RIGHT: Use HIGH only for actual emergencies
          System and team learns to ignore crying wolf
```

#### 6. Don't Forget Internal Notes
```
❌ WRONG: Sensitive info in public comments
✅ RIGHT: Use Internal Notes field for:
          - Budget/billing info
          - Customer escalation notes
          - Confidential technical details
```

---

## FAQ & Troubleshooting

### Q: How do I know what ticket to work on?

**A:** Check your dashboard:
1. Go to http://localhost:8000/helpdesk
2. See "My Tickets" section
3. Work on items in order:
   - 🔴 RED (Overdue SLA) - IMMEDIATE
   - 🟡 YELLOW (At risk) - URGENT
   - 🟢 GREEN (On track) - Normal priority

### Q: I can't find a ticket I created

**A:** Try these searches:
```
Search by your name:
- Go to http://localhost:8000/app/hd-ticket
- Filter: Created By = Your Name

Search by keywords:
- Use search box at top
- Type keywords from ticket subject

Search by date:
- Filter: Creation Date = "This Week"
```

### Q: How do I know if I'm meeting SLA?

**A:** Look at the **SLA Status** indicator on each ticket:
- 🟢 GREEN = On track (no action needed)
- 🟡 YELLOW = At risk (less than 25% time left - get help)
- 🔴 RED = OVERDUE (alert manager, escalate now)

### Q: Can I reopen a closed ticket?

**A:** If customer finds issue, you can:
1. Open the closed ticket
2. Click "Reopen"
3. Status changes back to "RESOLVED"
4. Continue working
5. New SLA clock starts

### Q: How do I see tickets from the whole team?

**A:** 
```
Go to: http://localhost:8000/app/hd-ticket
(This shows ALL tickets, not just yours)

Filter by team member if needed:
- Assigned To = Specific person
- Department = Infrastructure
```

### Q: What if I don't know how to fix something?

**A:** Use ticket comments to ask for help:
```
@RajKumar - I'm stuck on this SSL certificate error
            Can you take a look?

System notifies Raj immediately
He can comment with guidance or take over ticket
```

### Q: Can I search for specific types of tickets?

**A:** Yes! Filter by Type:
```
Type = "CI/CD Pipeline"      → Show only pipeline issues
Type = "Database"            → Show only DB issues
Type = "Server/Infrastructure" → Show only server issues
Type = "Security/Credentials"  → Show only security issues
```

### Q: How do I track if we're improving?

**A:** Check dashboard statistics:
```
Dashboard shows:
- Avg resolution time: [X hours]
- SLA success rate: [X%]
- Tickets created this month: [X]
- Tickets closed this month: [X]
```

Compare week to week to see improvements.

### Q: What if ticket is marked wrong Priority?

**A:** Anyone can update it:
1. Open the ticket
2. Click Priority field
3. Select correct priority
4. Save

If it was LOW but turns out CRITICAL:
- Change to HIGH
- Add comment: "Escalated - actual impact is company-wide"
- System extends SLA deadline

---

## Common Issues & Solutions

### Issue: "I missed my SLA deadline"

**What to do:**
1. Update ticket status to show you're still working
2. Add comment explaining delay
3. Alert your manager
4. Plan how to prevent next time

**Prevention:** Set phone alarm 30 min before deadline

---

### Issue: "Customer is complaining about response time"

**What to do:**
1. Update ticket immediately
2. Add comment: "Reviewing now, will have update in 30 min"
3. Keep customer informed every 30 minutes
4. Even "still investigating" is better than silence

---

### Issue: "I need help from multiple teams"

**What to do:**
```
Add comments mentioning multiple people:

@DatabaseTeam - Are these queries optimized?
@SecurityTeam - Is this connection safe?
@DevOpsTeam - Can someone review the deployment?

Each person gets notified
Everyone can see the conversation
```

---

### Issue: "Ticket is old and not fixed"

**What to do:**
1. Reopen the ticket if closed
2. Search for related tickets (might be a duplicate)
3. Contact originally assigned person
4. Request escalation to team lead

---

## Reporting & Analytics

### Getting Team Statistics

**Go to dashboard to see:**
```
http://localhost:8000/app/hd-settings

Metrics displayed:
- Total tickets this month
- Tickets resolved this month
- Average resolution time
- SLA success rate (% within SLA)
- Most common ticket types
- Peak days/times
```

### Exporting Tickets for Review

**You can export ticket data:**
1. Go to http://localhost:8000/app/hd-ticket
2. Click "Menu" (⋮)
3. Select "Export to CSV"
4. Open in Excel for your own analysis

**Use cases:**
- Identify repeat issues
- Plan staffing by ticket volume
- Track improvements over time
- Present to management

---

## Quick Reference - Cheat Sheet

### Most Common Actions

| Need To... | Go To... | What To Do |
|-----------|----------|-----------|
| Create ticket | http://localhost:8000/app/hd-ticket/new | Click "New", fill form, Save |
| View my tickets | http://localhost:8000/helpdesk | Scroll to "My Tickets" |
| Search all tickets | http://localhost:8000/app/hd-ticket | Type in search box |
| Filter by status | http://localhost:8000/app/hd-ticket | Click Filter, select Status |
| Assign to me | Open ticket | Click "Assign To", select your name |
| Reassign to someone | Open ticket | Click "Assigned To", type their name |
| Update status | Open ticket | Click Status, select new status |
| Add comment | Open ticket | Scroll to Comments, type, Post |
| Update priority | Open ticket | Click Priority field, select level |
| See SLA status | Open ticket | Look for green/yellow/red indicator |

### Important URLs

```
Dashboard:           http://localhost:8000/helpdesk
All Tickets:         http://localhost:8000/app/hd-ticket
Create New Ticket:   http://localhost:8000/app/hd-ticket/new
Settings:            http://localhost:8000/app/hd-settings
Reports:             http://localhost:8000/app/helpdesk/report
```

### Keyboard Shortcuts

```
Ctrl + K              Open search
Ctrl + Enter          Submit/Save form
Esc                   Close popup/modal
/ (forward slash)     Quick filter in list
```

---

## Getting Help

### If you need support:

1. **Ask a team member** - Use @mention in ticket comments
2. **Contact your team lead** - Email or Slack
3. **Check this guide** - Search for keyword
4. **Check system status** - http://localhost:8000/helpdesk

### If there's a technical issue:

1. **Check if it's a browser issue** - Try different browser
2. **Clear cache** - Ctrl+Shift+Delete
3. **Restart browser** - Fully close and reopen
4. **Check server status** - Is Docker running? (Ask your admin)

---

## Summary

### The Helpdesk System Helps Your Team By:

✅ **Creating a record** of every issue and solution  
✅ **Tracking time** so you know how fast you're working  
✅ **Managing priorities** so urgent things get done first  
✅ **Enabling teamwork** through comments and mentions  
✅ **Providing accountability** with SLA tracking  
✅ **Organizing knowledge** for future reference  
✅ **Showing metrics** so you can improve  

### You should:

1. **Create tickets** for all problems (don't rely on memory)
2. **Update status** as you work
3. **Add comments** frequently with progress
4. **Meet SLA** by responding and resolving on time
5. **Help teammates** by mentioning them when needed
6. **Document solutions** so others can learn

---

## Next Steps

1. **Login now:** http://localhost:8000/helpdesk (Admin/admin)
2. **Try it:** Create 1 test ticket
3. **Practice:** Add 3 comments
4. **Change status:** From NEW → IN PROGRESS → RESOLVED
5. **Show your team:** Demo the system in standup

---

**Remember:** The better you use the ticketing system, the more organized your team becomes! 🚀

---

*Need help? Ask your team lead or find them in ticket comments with @mention*

*Last Updated: May 12, 2026*  
*Version: 1.0 - Complete User Guide*
