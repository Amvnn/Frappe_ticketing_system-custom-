"""
Slack Integration for Frappe Helpdesk

Provides two capabilities:
1. Outbound notifications — posts a Block Kit message to a Slack channel when a new HD Ticket is created.
2. Slash command — /ticket <description> creates an HD Ticket from Slack.

Setup:
1. Create a Slack app at https://api.slack.com/apps
2. Enable Slash Commands, set Request URL to:
   https://<your-site>/api/method/helpdesk.api.slack.handle_ticket_command
3. Add OAuth scopes: chat:write, commands, users:read, users:read.email
4. Install to workspace and copy Bot Token + Signing Secret to HD Settings.
"""

import hashlib
import hmac
from time import time
from typing import Optional

import frappe
import requests
from frappe import _


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_slack_settings() -> dict:
    """Read Slack configuration from HD Settings.

    Returns a dict with keys: enable_slack_integration, slack_bot_token,
    slack_signing_secret, slack_notification_channel.

    Raises frappe.PermissionError if the signing secret is not configured.
    """
    settings = frappe.get_cached_doc("HD Settings")
    signing_secret = settings.get_password("slack_signing_secret", raise_exception=False)

    if not signing_secret:
        frappe.throw(
            _("Slack Signing Secret is not configured in HD Settings"),
            frappe.PermissionError,
        )

    return {
        "enable_slack_integration": settings.enable_slack_integration,
        "slack_bot_token": settings.get_password("slack_bot_token", raise_exception=False),
        "slack_signing_secret": signing_secret,
        "slack_notification_channel": settings.slack_notification_channel,
    }


def _build_ticket_blocks(ticket) -> list:
    """Return a Slack Block Kit payload for the given HD Ticket document."""
    ticket_url = f"{frappe.utils.get_url()}/helpdesk/tickets/{ticket.name}"

    return [
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Ticket:*\n{ticket.name}"},
                {"type": "mrkdwn", "text": f"*Priority:*\n{ticket.priority or 'Medium'}"},
                {"type": "mrkdwn", "text": f"*Subject:*\n{ticket.subject}"},
                {"type": "mrkdwn", "text": f"*Raised by:*\n{ticket.raised_by}"},
                {"type": "mrkdwn", "text": f"*Type:*\n{ticket.ticket_type or '—'}"},
                {"type": "mrkdwn", "text": f"*URL:*\n{ticket_url}"},
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open in Helpdesk"},
                    "url": ticket_url,
                }
            ],
        },
    ]


def _ephemeral(text: str, blocks: Optional[list] = None) -> dict:
    """Build an ephemeral Slack response dict."""
    response: dict = {"response_type": "ephemeral", "text": text}
    if blocks:
        response["blocks"] = blocks
    return response


# ---------------------------------------------------------------------------
# Signature verification (Requirement 3)
# ---------------------------------------------------------------------------


def verify_slack_request(timestamp: str, signature: str, raw_body: bytes) -> bool:
    """Verify an incoming Slack request using HMAC-SHA256.

    Args:
        timestamp: Value of the X-Slack-Request-Timestamp header.
        signature: Value of the X-Slack-Signature header (e.g. "v0=abc123...").
        raw_body: The raw request body bytes.

    Returns:
        True if the request is valid and fresh, False otherwise.
    """
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    # Reject stale requests (replay-attack prevention)
    if abs(time() - ts) > 300:
        return False

    settings = _get_slack_settings()
    signing_secret = settings["slack_signing_secret"]

    body_str = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body
    sig_basestring = f"v0:{timestamp}:{body_str}".encode("utf-8")

    computed = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring,
            hashlib.sha256,
        ).hexdigest()
    )

    # Constant-time comparison to prevent timing attacks (Requirement 3.4)
    return hmac.compare_digest(computed, signature)


# ---------------------------------------------------------------------------
# Outbound notification (Requirement 2)
# ---------------------------------------------------------------------------


def send_ticket_notification(ticket_name: str) -> None:
    """Post a Block Kit message to the configured Slack channel for the given ticket.

    Called via frappe.enqueue from enqueue_ticket_notification.
    Silently returns if the integration is disabled.
    Logs errors without re-raising so ticket creation is never rolled back.
    """
    try:
        settings = _get_slack_settings()
    except frappe.PermissionError:
        # Signing secret not configured — skip silently
        return

    if not settings["enable_slack_integration"]:
        return

    bot_token = settings["slack_bot_token"]
    channel = settings["slack_notification_channel"]

    if not bot_token or not channel:
        return

    try:
        ticket = frappe.get_doc("HD Ticket", ticket_name)
        blocks = _build_ticket_blocks(ticket)

        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        }
        payload = {"channel": channel, "blocks": blocks}

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            frappe.log_error(
                title="Slack Notification Failed",
                message=f"Slack API error for ticket {ticket_name}: {result.get('error')}",
            )
    except Exception:
        frappe.log_error(
            title="Slack Notification Failed",
            message=frappe.get_traceback(),
        )


# ---------------------------------------------------------------------------
# Hook-compatible enqueue wrapper (Requirement 2.3)
# ---------------------------------------------------------------------------


def enqueue_ticket_notification(doc, method: str) -> None:
    """after_insert hook wrapper — enqueues send_ticket_notification if enabled.

    Checks the toggle before enqueuing to avoid unnecessary background jobs.
    """
    try:
        settings = frappe.get_cached_doc("HD Settings")
    except Exception:
        return

    if not settings.enable_slack_integration:
        return

    frappe.enqueue(
        "helpdesk.api.slack.send_ticket_notification",
        ticket_name=doc.name,
        queue="default",
        enqueue_after_commit=True,
    )


# ---------------------------------------------------------------------------
# Slack user resolution (Requirement 5)
# ---------------------------------------------------------------------------


def resolve_slack_user(slack_user_id: str) -> Optional[str]:
    """Resolve a Slack user ID to a Frappe User email.

    Calls the Slack users.info API, then finds or creates a Frappe User.

    Returns the email string on success, or None on any failure.
    """
    try:
        settings = _get_slack_settings()
    except frappe.PermissionError:
        return None

    bot_token = settings["slack_bot_token"]
    if not bot_token:
        return None

    try:
        headers = {"Authorization": f"Bearer {bot_token}"}
        response = requests.get(
            "https://slack.com/api/users.info",
            params={"user": slack_user_id},
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        frappe.log_error(
            title="Slack User Resolution Failed",
            message=frappe.get_traceback(),
        )
        return None

    # Requirement 5.5 — treat ok: false as failure
    if not data.get("ok"):
        return None

    user_profile = data.get("user", {}).get("profile", {})
    email = user_profile.get("email")
    if not email:
        return None

    # Requirement 5.2 — reuse existing user; 5.3 — create if absent
    if not frappe.db.exists("User", email):
        display_name = data.get("user", {}).get("real_name") or email.split("@")[0]
        first_name = display_name.split(" ")[0]
        last_name = " ".join(display_name.split(" ")[1:]) or ""

        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)

    return email


# ---------------------------------------------------------------------------
# Slash command handler (Requirements 3, 4, 6)
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def handle_ticket_command() -> dict:
    """Handle the /ticket slash command from Slack.

    Verifies the request signature, resolves the Slack user, creates an HD Ticket
    synchronously (to stay within Slack's 3-second timeout), then enqueues the
    channel notification as a background job.

    Returns an ephemeral JSON response in all cases.
    """
    request = frappe.local.request
    raw_body: bytes = request.get_data()
    form = request.form

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Requirement 3 — verify signature; raises PermissionError / returns 403 on failure
    if not verify_slack_request(timestamp, signature, raw_body):
        frappe.throw(_("Slack signature verification failed"), frappe.PermissionError)

    text: str = (form.get("text") or "").strip()
    slack_user_id: str = form.get("user_id", "")
    slack_user_name: str = form.get("user_name", "")
    channel_name: str = form.get("channel_name", "")

    # Requirement 4.6 — empty command text
    if not text:
        return _ephemeral("Usage: `/ticket <description of the issue>`")

    # Requirement 5 — resolve Slack user to Frappe email
    email = resolve_slack_user(slack_user_id)
    if not email:
        return _ephemeral(
            "❌ Could not resolve your Slack account to a Helpdesk user. "
            "Please contact your administrator."
        )

    # Requirement 4 — create ticket synchronously
    try:
        description = (
            f"*Created via Slack* by @{slack_user_name} in #{channel_name}\n\n{text}"
        )
        ticket = frappe.get_doc(
            {
                "doctype": "HD Ticket",
                "subject": text[:200],
                "description": description,
                "raised_by": email,
                "priority": "Medium",
            }
        ).insert(ignore_permissions=True)

        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="Slack Ticket Creation Failed",
            message=frappe.get_traceback(),
        )
        return _ephemeral(
            "❌ An error occurred while creating the ticket. Please try again or contact your administrator."
        )

    # Enqueue channel notification (deferred so we stay within Slack's 3-second window)
    try:
        settings = frappe.get_cached_doc("HD Settings")
        if settings.enable_slack_integration:
            frappe.enqueue(
                "helpdesk.api.slack.send_ticket_notification",
                ticket_name=ticket.name,
                queue="default",
                enqueue_after_commit=True,
            )
    except Exception:
        # Non-fatal — ticket was already created
        frappe.log_error(
            title="Slack Notification Enqueue Failed",
            message=frappe.get_traceback(),
        )

    # Requirement 6.2 — success response with ticket name, subject preview, and button
    ticket_url = f"{frappe.utils.get_url()}/helpdesk/tickets/{ticket.name}"
    subject_preview = text[:100]

    success_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ Ticket *{ticket.name}* created\n{subject_preview}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open in Helpdesk"},
                    "url": ticket_url,
                }
            ],
        },
    ]

    return _ephemeral(f"Ticket {ticket.name} created.", blocks=success_blocks)
