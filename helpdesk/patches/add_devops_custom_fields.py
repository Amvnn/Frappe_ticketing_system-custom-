"""
Migration Patch: Add DevOps-specific custom fields to HD Ticket
This patch adds custom fields optimized for DevOps ticketing workflow
Run via: bench --site helpdesk.localhost execute helpdesk.patches.add_devops_custom_fields.execute
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Create custom fields for DevOps ticketing"""
    
    custom_fields = {
        "HD Ticket": [
            {
                "fieldname": "devops_section",
                "label": "DevOps Information",
                "fieldtype": "Section Break",
                "insert_after": "description",
                "permlevel": 0
            },
            {
                "fieldname": "department",
                "label": "Department / Branch",
                "fieldtype": "Select",
                "options": "Engineering\nData Science\nBackend\nFrontend\nInfrastructure\nQA\nOther",
                "insert_after": "devops_section",
                "permlevel": 0,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "reqd": 0,
                "help": "Which department / branch is raising this ticket?"
            },
            {
                "fieldname": "project_name",
                "label": "Project Name",
                "fieldtype": "Data",
                "insert_after": "department",
                "permlevel": 0,
                "in_list_view": 1,
                "reqd": 0,
                "help": "Project or system name (e.g. 'API Gateway', 'Data Pipeline')"
            },
            {
                "fieldname": "environment",
                "label": "Environment",
                "fieldtype": "Select",
                "options": "Development\nStaging\nProduction",
                "insert_after": "project_name",
                "permlevel": 0,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "reqd": 0,
                "help": "Which environment is affected?"
            },
            {
                "fieldname": "impact_scope",
                "label": "Impact Scope",
                "fieldtype": "Select",
                "options": "Single User\nTeam\nService-Wide\nCompany-Wide",
                "insert_after": "environment",
                "permlevel": 0,
                "reqd": 0,
                "help": "How many users are affected?"
            },
            {
                "fieldname": "devops_column_break",
                "fieldtype": "Column Break",
                "insert_after": "impact_scope",
                "permlevel": 0
            },
            {
                "fieldname": "error_code",
                "label": "Error Code / Exit Status",
                "fieldtype": "Data",
                "insert_after": "devops_column_break",
                "permlevel": 0,
                "help": "e.g. '503', 'SIGTERM', 'OOM Killed'"
            },
            {
                "fieldname": "affected_service",
                "label": "Affected Service / Component",
                "fieldtype": "Data",
                "insert_after": "error_code",
                "permlevel": 0,
                "help": "e.g. 'API Server', 'Database', 'Load Balancer'"
            },
            {
                "fieldname": "internal_section",
                "label": "Internal (DevOps Only)",
                "fieldtype": "Section Break",
                "insert_after": "affected_service",
                "permlevel": 0
            },
            {
                "fieldname": "internal_notes",
                "label": "Internal Notes",
                "fieldtype": "Text Editor",
                "insert_after": "internal_section",
                "permlevel": 0,
                "read_only": 0,
                "help": "Visible only to DevOps team - technical discussion, debugging steps"
            },
            {
                "fieldname": "root_cause",
                "label": "Root Cause",
                "fieldtype": "Text",
                "insert_after": "internal_notes",
                "permlevel": 0,
                "read_only": 0,
                "help": "Fill this before closing - what was the root cause?"
            },
            {
                "fieldname": "resolution_steps",
                "label": "Resolution Steps Taken",
                "fieldtype": "Text Editor",
                "insert_after": "root_cause",
                "permlevel": 0,
                "read_only": 0,
                "help": "What did we do to fix it?"
            },
            {
                "fieldname": "prevention",
                "label": "How to Prevent in Future",
                "fieldtype": "Text Editor",
                "insert_after": "resolution_steps",
                "permlevel": 0,
                "read_only": 0,
                "help": "Monitoring improvements, alerts, tests, docs, etc."
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    
    frappe.db.commit()
    frappe.msgprint("✅ DevOps custom fields added successfully")


if __name__ == "__main__":
    execute()
