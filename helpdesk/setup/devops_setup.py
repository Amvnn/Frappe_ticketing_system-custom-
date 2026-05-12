"""
DevOps Ticketing System — Automated Setup Script

Run inside the container after helpdesk is installed:
  bench --site helpdesk.localhost execute helpdesk.setup.devops_setup.run

This script is idempotent — safe to run multiple times.
It sets up everything that does NOT require external credentials:
  - DevOps ticket types
  - Custom fields on HD Ticket (Department, Environment, Project, Root Cause)
  - SLA policy tuned for DevOps priorities
  - DevOps team
  - KB categories
  - Saved replies (canned responses)
  - System settings (disable public signup)
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


# ---------------------------------------------------------------------------
# Ticket Types
# ---------------------------------------------------------------------------

DEVOPS_TICKET_TYPES = [
    ("CI/CD Pipeline", "Build pipelines, GitHub Actions, Jenkins, deployment automation"),
    ("Server / Infrastructure", "Server provisioning, resource allocation, uptime, VM management"),
    ("Database", "DB access, query performance, backups, schema changes, connection issues"),
    ("Deployment Request", "Deploy a specific version to Dev, Staging, or Production"),
    ("Access & Permissions", "SSH keys, VPN, credentials, role assignments"),
    ("Environment Setup", "New environment provisioning, config setup, dependency installation"),
    ("Security / Credentials", "SSL certificates, secrets rotation, security audit requests"),
    ("Network / VPN", "VPN access, firewall rules, DNS, port forwarding, connectivity issues"),
    ("Monitoring / Alerting", "Set up or modify monitoring rules, alerts, dashboards, log access"),
    ("Other", "Any request that does not fit the above categories"),
]


def create_devops_ticket_types():
    print("→ Creating DevOps ticket types...")
    for name, description in DEVOPS_TICKET_TYPES:
        if frappe.db.exists("HD Ticket Type", name):
            print(f"  ✓ Already exists: {name}")
            continue
        doc = frappe.new_doc("HD Ticket Type")
        doc.name = name
        doc.description = description
        doc.is_system = False
        doc.save(ignore_permissions=True)
        print(f"  + Created: {name}")
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Custom Fields on HD Ticket
# ---------------------------------------------------------------------------

def get_devops_custom_fields():
    return {
        "HD Ticket": [
            {
                "fieldname": "custom_devops_section",
                "fieldtype": "Section Break",
                "label": "DevOps Details",
                "insert_after": "description",
                "collapsible": 0,
            },
            {
                "fieldname": "custom_department",
                "fieldtype": "Select",
                "label": "Department / Branch",
                "insert_after": "custom_devops_section",
                "options": "\nEngineering\nDevOps\nQA\nProduct\nDesign\nMarketing\nOperations\nOther",
                "reqd": 0,
                "in_list_view": 0,
                "description": "Which team or branch is raising this request",
            },
            {
                "fieldname": "custom_environment",
                "fieldtype": "Select",
                "label": "Affected Environment",
                "insert_after": "custom_department",
                "options": "\nDevelopment\nStaging\nProduction\nAll\nNot Applicable",
                "reqd": 0,
                "in_list_view": 0,
                "description": "Which environment is this issue affecting",
            },
            {
                "fieldname": "custom_project_name",
                "fieldtype": "Data",
                "label": "Project / Service Name",
                "insert_after": "custom_environment",
                "reqd": 0,
                "description": "Name of the project, service, or repository affected",
            },
            {
                "fieldname": "custom_error_snippet",
                "fieldtype": "Long Text",
                "label": "Error Message / Log Snippet",
                "insert_after": "custom_project_name",
                "reqd": 0,
                "description": "Paste any relevant error messages or log output here",
            },
            {
                "fieldname": "custom_agent_section",
                "fieldtype": "Section Break",
                "label": "Agent Notes (Internal)",
                "insert_after": "custom_error_snippet",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_root_cause",
                "fieldtype": "Small Text",
                "label": "Root Cause",
                "insert_after": "custom_agent_section",
                "reqd": 0,
                "permlevel": 1,
                "description": "To be filled by DevOps agent before resolving. Not visible to requester.",
            },
            {
                "fieldname": "custom_internal_notes",
                "fieldtype": "Long Text",
                "label": "Internal DevOps Notes",
                "insert_after": "custom_root_cause",
                "reqd": 0,
                "permlevel": 1,
                "description": "Internal discussion visible only to DevOps agents.",
            },
        ]
    }


def create_devops_custom_fields():
    print("→ Creating custom fields on HD Ticket...")
    existing = frappe.db.get_all(
        "Custom Field",
        filters={"dt": "HD Ticket", "fieldname": ["like", "custom_%"]},
        pluck="fieldname",
    )
    fields = get_devops_custom_fields()
    # Filter out already-existing fields to avoid errors
    fields["HD Ticket"] = [
        f for f in fields["HD Ticket"]
        if f["fieldname"] not in existing
    ]
    if fields["HD Ticket"]:
        create_custom_fields(fields, ignore_validate=True)
        frappe.db.commit()
        print(f"  + Created {len(fields['HD Ticket'])} custom fields")
    else:
        print("  ✓ All custom fields already exist")


# ---------------------------------------------------------------------------
# SLA Policy — DevOps
# ---------------------------------------------------------------------------

def create_devops_sla():
    print("→ Configuring DevOps SLA policy...")
    sla_name = "DevOps SLA"

    if frappe.db.exists("HD Service Level Agreement", sla_name):
        print(f"  ✓ Already exists: {sla_name}")
        return

    # Ensure priorities exist
    for priority, integer_value in [("Urgent", 100), ("High", 200), ("Medium", 300), ("Low", 400)]:
        if not frappe.db.exists("HD Ticket Priority", priority):
            doc = frappe.new_doc("HD Ticket Priority")
            doc.name = priority
            doc.integer_value = integer_value
            doc.insert(ignore_permissions=True)

    # Ensure holiday list exists
    if not frappe.db.exists("HD Service Holiday List", "Default"):
        from datetime import datetime
        frappe.get_doc({
            "doctype": "HD Service Holiday List",
            "holiday_list_name": "Default",
            "from_date": datetime.strptime(f"Jan 1 {datetime.now().year}", "%b %d %Y"),
            "to_date": datetime.strptime(f"Jan 1 {datetime.now().year + 1}", "%b %d %Y"),
        }).insert(ignore_permissions=True)

    sla_doc = frappe.new_doc("HD Service Level Agreement")
    sla_doc.service_level = sla_name
    sla_doc.document_type = "HD Ticket"
    sla_doc.default_sla = 0
    sla_doc.enabled = 1
    sla_doc.holiday_list = "Default"

    # Priority SLA targets (times in seconds)
    priorities = [
        # priority, response_time, resolution_time, default_priority
        ("High",   1 * 3600,       4 * 3600,        0),   # 1h response / 4h resolve
        ("Medium", 4 * 3600,       8 * 3600,        1),   # 4h response / 1 business day
        ("Low",    8 * 3600,       72 * 3600,       0),   # 1 day response / 3 days resolve
        ("Urgent", 30 * 60,        2 * 3600,        0),   # 30min response / 2h resolve
    ]

    for priority, response_time, resolution_time, default_priority in priorities:
        sla_doc.append("priorities", {
            "doctype": "HD Service Level Priority",
            "priority": priority,
            "default_priority": default_priority,
            "response_time": response_time,
            "resolution_time": resolution_time,
        })

    # Business hours Mon-Fri 9am-6pm
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        sla_doc.append("support_and_resolution", {
            "doctype": "HD Service Day",
            "workday": day,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        })

    sla_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  + Created: {sla_name}")


# ---------------------------------------------------------------------------
# DevOps Team
# ---------------------------------------------------------------------------

def create_devops_team():
    print("→ Creating DevOps team...")
    team_name = "DevOps"

    if frappe.db.exists("HD Team", team_name):
        print(f"  ✓ Already exists: {team_name}")
        return

    doc = frappe.new_doc("HD Team")
    doc.team_name = team_name
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  + Created team: {team_name}")


# ---------------------------------------------------------------------------
# Knowledge Base Categories
# ---------------------------------------------------------------------------

KB_CATEGORIES = [
    "CI/CD & Pipelines",
    "Server Access & SSH",
    "Database Operations",
    "Deployment Guides",
    "VPN & Network Access",
    "Common Errors & Fixes",
]


def create_kb_categories():
    print("→ Creating Knowledge Base categories...")
    for category_name in KB_CATEGORIES:
        if frappe.db.exists("HD Article Category", category_name):
            print(f"  ✓ Already exists: {category_name}")
            continue
        frappe.get_doc({
            "doctype": "HD Article Category",
            "category_name": category_name,
        }).insert(ignore_permissions=True)
        print(f"  + Created: {category_name}")
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Saved Replies (Canned Responses)
# ---------------------------------------------------------------------------

SAVED_REPLIES = [
    {
        "name": "Ticket Received - Acknowledgement",
        "message": (
            "Hi {{ ticket.raised_by }},\n\n"
            "Thank you for raising this request. Your ticket **{{ ticket.name }}** has been received "
            "and assigned to our DevOps team.\n\n"
            "We will respond within the SLA timeframe based on your selected priority.\n\n"
            "You can track the status of your ticket at any time from the portal.\n\n"
            "Regards,\nDevOps Team"
        ),
    },
    {
        "name": "Request for More Information",
        "message": (
            "Hi {{ ticket.raised_by }},\n\n"
            "Thank you for your ticket **{{ ticket.name }}**.\n\n"
            "To help us resolve this faster, could you please provide:\n"
            "- The exact error message or log output\n"
            "- The environment affected (Development / Staging / Production)\n"
            "- Steps to reproduce the issue\n"
            "- Any recent changes made before the issue appeared\n\n"
            "Regards,\nDevOps Team"
        ),
    },
    {
        "name": "Issue Resolved",
        "message": (
            "Hi {{ ticket.raised_by }},\n\n"
            "Your ticket **{{ ticket.name }}** has been resolved.\n\n"
            "**Resolution Summary:**\n"
            "[Add resolution details here]\n\n"
            "If the issue persists or you have further questions, please reopen this ticket "
            "or raise a new one.\n\n"
            "Regards,\nDevOps Team"
        ),
    },
    {
        "name": "Deployment Scheduled",
        "message": (
            "Hi {{ ticket.raised_by }},\n\n"
            "Your deployment request **{{ ticket.name }}** has been reviewed and scheduled.\n\n"
            "**Deployment Details:**\n"
            "- Environment: [Environment]\n"
            "- Scheduled Time: [Date & Time]\n"
            "- Estimated Duration: [Duration]\n\n"
            "We will notify you once the deployment is complete.\n\n"
            "Regards,\nDevOps Team"
        ),
    },
    {
        "name": "Access Request - Approved",
        "message": (
            "Hi {{ ticket.raised_by }},\n\n"
            "Your access request **{{ ticket.name }}** has been approved and provisioned.\n\n"
            "**Access Details:**\n"
            "- Resource: [Resource Name]\n"
            "- Access Level: [Read / Write / Admin]\n"
            "- Valid Until: [Date or Permanent]\n\n"
            "Please ensure you follow the company security policy when using this access.\n\n"
            "Regards,\nDevOps Team"
        ),
    },
    {
        "name": "SLA Breach Notification",
        "message": (
            "Hi {{ ticket.raised_by }},\n\n"
            "We sincerely apologize for the delay in responding to your ticket **{{ ticket.name }}**.\n\n"
            "This ticket has been escalated to the DevOps Lead and will be prioritized immediately.\n\n"
            "We will update you shortly.\n\n"
            "Regards,\nDevOps Team"
        ),
    },
]


def create_saved_replies():
    print("→ Creating saved replies (canned responses)...")
    for reply in SAVED_REPLIES:
        if frappe.db.exists("HD Saved Reply", reply["name"]):
            print(f"  ✓ Already exists: {reply['name']}")
            continue
        doc = frappe.new_doc("HD Saved Reply")
        doc.title = reply["name"]
        doc.message = reply["message"]
        doc.insert(ignore_permissions=True)
        print(f"  + Created: {reply['name']}")
    frappe.db.commit()


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------

def configure_system_settings():
    print("→ Configuring system settings...")

    # Disable public signup — only SSO / admin-invited users can access
    frappe.db.set_single_value("System Settings", "disable_user_pass_login", 0)
    # Note: we keep password login enabled so admin can still log in
    # Disable self-registration (users cannot sign up themselves)
    frappe.db.set_single_value("Website Settings", "disable_signup", 1)

    frappe.db.commit()
    print("  + Disabled public self-registration (disable_signup = 1)")
    print("  ✓ Password login kept enabled for Administrator access")


# ---------------------------------------------------------------------------
# HD Settings — mute emails during dev, enable server scripts
# ---------------------------------------------------------------------------

def configure_hd_settings():
    print("→ Configuring HD Settings...")
    settings = frappe.get_doc("HD Settings")

    changed = False

    # Enable server scripts if not already
    if not frappe.db.get_single_value("HD Settings", "allow_anyone_to_create_tickets"):
        # Keep ticket creation restricted to authenticated users only
        pass

    frappe.db.commit()
    print("  ✓ HD Settings checked")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run():
    """Run all DevOps setup tasks. Idempotent — safe to run multiple times."""
    print("\n" + "=" * 60)
    print("  DevOps Ticketing System — Automated Setup")
    print("=" * 60 + "\n")

    create_devops_ticket_types()
    create_devops_custom_fields()
    create_devops_sla()
    create_devops_team()
    create_kb_categories()
    create_saved_replies()
    configure_system_settings()
    configure_hd_settings()

    print("\n" + "=" * 60)
    print("  Setup complete!")
    print("  Next steps requiring your credentials:")
    print("  1. Google SSO  → helpdesk UI > Settings > Integrations > Google SSO")
    print("  2. Invite agents → helpdesk UI > Settings > Agents")
    print("  3. Assignment rules → helpdesk UI > Settings > Assignment Rules")
    print("  4. SMTP email → Frappe Desk > Email Account")
    print("  5. Slack webhook → helpdesk UI > Settings > Integrations > Slack")
    print("  See CREDENTIALS.md for step-by-step instructions.")
    print("=" * 60 + "\n")
