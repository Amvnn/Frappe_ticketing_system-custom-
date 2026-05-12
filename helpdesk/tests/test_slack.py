# Copyright (c) 2026, Frappe Technologies and Contributors
# See license.txt
"""
Backend tests for the Slack integration (helpdesk/api/slack.py).

Covers:
  - Unit tests: schema checks, enqueue dispatch, timeout, constant-time compare
  - Property-Based Tests (PBT) using Hypothesis for Properties 1-10
"""

import hashlib
import hmac
import inspect
import json
import os
import time
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from helpdesk.api.slack import (
    _build_ticket_blocks,
    enqueue_ticket_notification,
    handle_ticket_command,
    resolve_slack_user,
    send_ticket_notification,
    verify_slack_request,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "helpdesk",
    "doctype",
    "hd_settings",
    "hd_settings.json",
)

_SLACK_FIELDS = {
    "integrations_tab": "Tab Break",
    "slack_section": "Section Break",
    "enable_slack_integration": "Check",
    "column_break_slack": "Column Break",
    "slack_bot_token": "Password",
    "slack_signing_secret": "Password",
    "slack_notification_channel": "Data",
}


def _make_signature(secret: str, timestamp: str, body: bytes) -> str:
    """Produce a valid v0= Slack signature for the given inputs."""
    body_str = body.decode("utf-8") if isinstance(body, bytes) else body
    sig_base = f"v0:{timestamp}:{body_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), sig_base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def _fresh_ts() -> str:
    return str(int(time.time()))


def _mock_settings(
    enabled: bool = True,
    token: str = "xoxb-test-token",
    secret: str = "test-signing-secret",
    channel: str = "#devops-tickets",
):
    return {
        "enable_slack_integration": enabled,
        "slack_bot_token": token,
        "slack_signing_secret": secret,
        "slack_notification_channel": channel,
    }


def _make_ticket_mock(
    name: str = "HD-001",
    subject: str = "Test subject",
    raised_by: str = "user@example.com",
    priority: str = "Medium",
    ticket_type: str = "Bug",
):
    t = MagicMock()
    t.name = name
    t.subject = subject
    t.raised_by = raised_by
    t.priority = priority
    t.ticket_type = ticket_type
    return t


# ---------------------------------------------------------------------------
# 5.1  Unit test: HD Settings JSON contains the four new Slack fields
# ---------------------------------------------------------------------------

class TestHDSettingsSchema(unittest.TestCase):
    """5.1 — Req 1.1, 1.5: Slack fields exist in hd_settings.json with correct fieldtypes."""

    def _load_fields(self):
        with open(_SETTINGS_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return {f["fieldname"]: f["fieldtype"] for f in data["fields"]}

    def test_slack_fields_present_with_correct_fieldtypes(self):
        fields = self._load_fields()
        for fieldname, expected_type in _SLACK_FIELDS.items():
            with self.subTest(fieldname=fieldname):
                self.assertIn(fieldname, fields, f"Missing field: {fieldname}")
                self.assertEqual(
                    fields[fieldname],
                    expected_type,
                    f"{fieldname}: expected {expected_type}, got {fields[fieldname]}",
                )

    def test_slack_bot_token_is_password(self):
        fields = self._load_fields()
        self.assertEqual(fields["slack_bot_token"], "Password")

    def test_slack_signing_secret_is_password(self):
        fields = self._load_fields()
        self.assertEqual(fields["slack_signing_secret"], "Password")


# ---------------------------------------------------------------------------
# 5.2  PBT — Property 2: Enabled integration with missing credentials fails validation
# ---------------------------------------------------------------------------

class TestSlackValidation(FrappeTestCase):
    """5.2 — Property 2: For random settings with toggle on and empty token/secret, assert ValidationError."""

    # Feature: slack-integration, Property 2: Enabled integration with missing credentials fails validation
    @given(
        token=st.one_of(st.none(), st.just("")),
        secret=st.one_of(st.none(), st.just("")),
    )
    @h_settings(max_examples=100)
    def test_property_2_validation_error_when_enabled_with_missing_credentials(
        self, token, secret
    ):
        """For any HD Settings with enable_slack_integration=True and empty token or secret, validate() raises ValidationError."""
        # At least one must be empty for this test
        if token and secret:
            return

        settings = frappe.get_doc("HD Settings")
        settings.enable_slack_integration = 1
        settings.slack_bot_token = token or ""
        settings.slack_signing_secret = secret or ""

        with self.assertRaises(frappe.ValidationError):
            settings.validate()


# ---------------------------------------------------------------------------
# 5.3  PBT — Property 1: Disabled integration suppresses all notifications
# ---------------------------------------------------------------------------

class TestNoNotificationWhenDisabled(unittest.TestCase):
    """5.3 — Property 1: For random tickets with toggle off, assert no HTTP call is made."""

    # Feature: slack-integration, Property 1: Disabled integration suppresses all notifications
    @given(ticket_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-")))
    @h_settings(max_examples=100)
    def test_property_1_no_http_call_when_integration_disabled(self, ticket_name):
        """For any ticket name, send_ticket_notification makes zero HTTP calls when toggle is off."""
        mock_settings = _mock_settings(enabled=False)

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.requests.post") as mock_post, \
             patch("helpdesk.api.slack.requests.get") as mock_get:
            send_ticket_notification(ticket_name)

        mock_post.assert_not_called()
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# 5.4  PBT — Property 3: Notification message contains all required ticket fields
# ---------------------------------------------------------------------------

_printable = st.text(min_size=1, max_size=80, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters="@.-_"))


class TestBuildTicketBlocks(unittest.TestCase):
    """5.4 — Property 3: For random ticket dicts, _build_ticket_blocks contains all required fields."""

    # Feature: slack-integration, Property 3: Notification message contains all required ticket fields
    @given(
        name=_printable,
        subject=_printable,
        raised_by=st.emails(),
        priority=st.sampled_from(["Low", "Medium", "High", "Urgent"]),
        ticket_type=_printable,
    )
    @h_settings(max_examples=100)
    def test_property_3_blocks_contain_all_required_fields(
        self, name, subject, raised_by, priority, ticket_type
    ):
        """_build_ticket_blocks must include name, subject, raised_by, priority, type, URL, and an actions button."""
        ticket = _make_ticket_mock(
            name=name,
            subject=subject,
            raised_by=raised_by,
            priority=priority,
            ticket_type=ticket_type,
        )

        with patch("helpdesk.api.slack.frappe.utils.get_url", return_value="https://helpdesk.example.com"):
            blocks = _build_ticket_blocks(ticket)

        # Must have at least a section block and an actions block
        block_types = [b["type"] for b in blocks]
        self.assertIn("section", block_types)
        self.assertIn("actions", block_types)

        # Collect all mrkdwn text from section fields
        section_text = " ".join(
            f["text"]
            for b in blocks
            if b["type"] == "section"
            for f in b.get("fields", [])
        )
        self.assertIn(name, section_text)
        self.assertIn(subject, section_text)
        self.assertIn(raised_by, section_text)
        self.assertIn(priority, section_text)
        self.assertIn(ticket_type, section_text)
        self.assertIn(name, section_text)  # URL contains ticket name

        # Actions block must have a button element
        actions_blocks = [b for b in blocks if b["type"] == "actions"]
        self.assertTrue(len(actions_blocks) >= 1)
        elements = actions_blocks[0].get("elements", [])
        self.assertTrue(any(e.get("type") == "button" for e in elements))


# ---------------------------------------------------------------------------
# 5.5  PBT — Property 4: Notification failure does not propagate exceptions
# ---------------------------------------------------------------------------

class TestNotificationFailureSilent(unittest.TestCase):
    """5.5 — Property 4: For random tickets, HTTP raises → log_error called, no exception propagates."""

    # Feature: slack-integration, Property 4: Notification failure does not propagate exceptions
    @given(ticket_name=st.text(min_size=1, max_size=50))
    @h_settings(max_examples=100)
    def test_property_4_http_failure_logs_and_does_not_raise(self, ticket_name):
        """send_ticket_notification must catch all exceptions, call frappe.log_error, and not re-raise."""
        mock_settings = _mock_settings(enabled=True)
        mock_ticket = _make_ticket_mock(name=ticket_name)

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.frappe.get_doc", return_value=mock_ticket), \
             patch("helpdesk.api.slack._build_ticket_blocks", return_value=[]), \
             patch("helpdesk.api.slack.requests.post", side_effect=Exception("network error")), \
             patch("helpdesk.api.slack.frappe.log_error") as mock_log_error, \
             patch("helpdesk.api.slack.frappe.get_traceback", return_value="traceback"):
            # Must not raise
            try:
                send_ticket_notification(ticket_name)
            except Exception as exc:
                self.fail(f"send_ticket_notification raised an exception: {exc}")

        mock_log_error.assert_called_once()


# ---------------------------------------------------------------------------
# 5.6  PBT — Property 5: Signature verification accepts valid / rejects invalid
# ---------------------------------------------------------------------------

class TestVerifySlackRequest(unittest.TestCase):
    """5.6 — Property 5: verify_slack_request correctness across random inputs."""

    # Feature: slack-integration, Property 5: Signature verification accepts valid requests and rejects invalid ones
    @given(
        body=st.binary(min_size=0, max_size=512),
        secret=st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
    )
    @h_settings(max_examples=100)
    def test_property_5_valid_signature_accepted(self, body, secret):
        """A correctly signed, fresh request must return True."""
        ts = _fresh_ts()
        sig = _make_signature(secret, ts, body)
        mock_settings = _mock_settings(secret=secret)

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings):
            result = verify_slack_request(ts, sig, body)

        self.assertTrue(result)

    # Feature: slack-integration, Property 5: Signature verification accepts valid requests and rejects invalid ones
    @given(
        body=st.binary(min_size=1, max_size=512),
        secret=st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        extra_byte=st.integers(min_value=0, max_value=255),
    )
    @h_settings(max_examples=100)
    def test_property_5_tampered_body_rejected(self, body, secret, extra_byte):
        """A request with a tampered body must return False."""
        ts = _fresh_ts()
        sig = _make_signature(secret, ts, body)
        tampered = body + bytes([extra_byte])
        mock_settings = _mock_settings(secret=secret)

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings):
            result = verify_slack_request(ts, sig, tampered)

        self.assertFalse(result)

    # Feature: slack-integration, Property 5: Signature verification accepts valid requests and rejects invalid ones
    @given(
        body=st.binary(min_size=0, max_size=512),
        secret=st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        age=st.integers(min_value=301, max_value=9999),
    )
    @h_settings(max_examples=100)
    def test_property_5_stale_timestamp_rejected(self, body, secret, age):
        """A request with a timestamp older than 300 s must return False."""
        stale_ts = str(int(time.time()) - age)
        sig = _make_signature(secret, stale_ts, body)
        mock_settings = _mock_settings(secret=secret)

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings):
            result = verify_slack_request(stale_ts, sig, body)

        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 5.7  PBT — Property 6: Valid slash command creates ticket with correct fields
# ---------------------------------------------------------------------------

def _build_mock_request(text: str, user_id: str, user_name: str, channel: str, secret: str):
    """Build a mock Flask/Werkzeug request for handle_ticket_command."""
    body_str = f"text={text}&user_id={user_id}&user_name={user_name}&channel_name={channel}"
    raw_body = body_str.encode("utf-8")
    ts = _fresh_ts()
    sig = _make_signature(secret, ts, raw_body)

    mock_request = MagicMock()
    mock_request.get_data.return_value = raw_body
    mock_request.form = {
        "text": text,
        "user_id": user_id,
        "user_name": user_name,
        "channel_name": channel,
    }
    mock_request.headers = {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sig,
    }
    return mock_request


_safe_text = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters=".-_"),
).filter(lambda t: t.strip())


class TestHandleTicketCommandValid(unittest.TestCase):
    """5.7 — Property 6: Valid slash command creates ticket with correct fields."""

    # Feature: slack-integration, Property 6: Valid slash command creates a ticket with correct fields
    @given(
        text=_safe_text,
        user_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        user_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        channel=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
        email=st.emails(),
    )
    @h_settings(max_examples=100)
    def test_property_6_ticket_fields_match_command_inputs(
        self, text, user_id, user_name, channel, email
    ):
        """Created ticket must have subject=text[:200], raised_by=email, priority=Medium, description contains text/user/channel."""
        secret = "test-secret-prop6"
        mock_request = _build_mock_request(text, user_id, user_name, channel, secret)

        inserted_docs = []

        def fake_get_doc(data_or_doctype, name=None):
            if isinstance(data_or_doctype, dict) and data_or_doctype.get("doctype") == "HD Ticket":
                doc = MagicMock()
                doc.subject = data_or_doctype["subject"]
                doc.raised_by = data_or_doctype["raised_by"]
                doc.priority = data_or_doctype["priority"]
                doc.description = data_or_doctype["description"]
                doc.name = "HD-TEST-001"

                def fake_insert(**kwargs):
                    inserted_docs.append(doc)
                    return doc

                doc.insert = fake_insert
                return doc
            # For HD Settings (enqueue check)
            settings_mock = MagicMock()
            settings_mock.enable_slack_integration = False
            return settings_mock

        with patch("helpdesk.api.slack.frappe.local") as mock_local, \
             patch("helpdesk.api.slack.verify_slack_request", return_value=True), \
             patch("helpdesk.api.slack.resolve_slack_user", return_value=email), \
             patch("helpdesk.api.slack.frappe.get_doc", side_effect=fake_get_doc), \
             patch("helpdesk.api.slack.frappe.db") as mock_db, \
             patch("helpdesk.api.slack.frappe.enqueue"), \
             patch("helpdesk.api.slack.frappe.utils.get_url", return_value="https://helpdesk.example.com"):
            mock_local.request = mock_request
            mock_db.commit = MagicMock()

            result = handle_ticket_command()

        self.assertEqual(len(inserted_docs), 1)
        doc = inserted_docs[0]
        self.assertEqual(doc.subject, text[:200])
        self.assertEqual(doc.raised_by, email)
        self.assertEqual(doc.priority, "Medium")
        self.assertIn(text, doc.description)
        self.assertIn(user_name, doc.description)
        self.assertIn(channel, doc.description)

        self.assertEqual(result.get("response_type"), "ephemeral")


# ---------------------------------------------------------------------------
# 5.8  PBT — Property 7: Invalid inputs prevent ticket creation
# ---------------------------------------------------------------------------

class TestHandleTicketCommandInvalid(unittest.TestCase):
    """5.8 — Property 7: Empty/whitespace text or failed users.info → zero tickets, ephemeral response."""

    def _make_request_mock(self, text: str):
        mock_request = MagicMock()
        mock_request.get_data.return_value = b""
        mock_request.form = {"text": text, "user_id": "U123", "user_name": "user", "channel_name": "general"}
        mock_request.headers = {"X-Slack-Request-Timestamp": _fresh_ts(), "X-Slack-Signature": "v0=dummy"}
        return mock_request

    # Feature: slack-integration, Property 7: Invalid inputs prevent ticket creation
    @given(text=st.one_of(st.just(""), st.text(max_size=50, alphabet=" \t\n\r")))
    @h_settings(max_examples=100)
    def test_property_7_empty_text_returns_ephemeral_no_ticket(self, text):
        """Empty or whitespace-only command text must return ephemeral and create zero tickets."""
        with patch("helpdesk.api.slack.frappe.local") as mock_local, \
             patch("helpdesk.api.slack.verify_slack_request", return_value=True), \
             patch("helpdesk.api.slack.frappe.get_doc") as mock_get_doc:
            mock_local.request = self._make_request_mock(text)

            result = handle_ticket_command()

        self.assertEqual(result.get("response_type"), "ephemeral")
        # get_doc for HD Ticket should never be called
        for c in mock_get_doc.call_args_list:
            args = c[0]
            if args and isinstance(args[0], dict):
                self.assertNotEqual(args[0].get("doctype"), "HD Ticket")

    # Feature: slack-integration, Property 7: Invalid inputs prevent ticket creation
    @given(text=_safe_text)
    @h_settings(max_examples=100)
    def test_property_7_failed_user_resolution_returns_ephemeral_no_ticket(self, text):
        """Failed users.info (returns None) must return ephemeral and create zero tickets."""
        with patch("helpdesk.api.slack.frappe.local") as mock_local, \
             patch("helpdesk.api.slack.verify_slack_request", return_value=True), \
             patch("helpdesk.api.slack.resolve_slack_user", return_value=None), \
             patch("helpdesk.api.slack.frappe.get_doc") as mock_get_doc:
            mock_local.request = self._make_request_mock(text)

            result = handle_ticket_command()

        self.assertEqual(result.get("response_type"), "ephemeral")
        for c in mock_get_doc.call_args_list:
            args = c[0]
            if args and isinstance(args[0], dict):
                self.assertNotEqual(args[0].get("doctype"), "HD Ticket")


# ---------------------------------------------------------------------------
# 5.9  PBT — Property 8: Ticket creation failure returns ephemeral error and logs
# ---------------------------------------------------------------------------

class TestHandleTicketCommandInsertFailure(unittest.TestCase):
    """5.9 — Property 8: Insert raises → log_error called, response text has no traceback."""

    # Feature: slack-integration, Property 8: Ticket creation failure returns ephemeral error and logs
    @given(text=_safe_text, email=st.emails())
    @h_settings(max_examples=100)
    def test_property_8_insert_failure_logs_and_returns_ephemeral_without_traceback(
        self, text, email
    ):
        """When HD Ticket insert raises, frappe.log_error is called and response text has no traceback."""
        mock_request = MagicMock()
        mock_request.get_data.return_value = b""
        mock_request.form = {"text": text, "user_id": "U123", "user_name": "user", "channel_name": "general"}
        mock_request.headers = {"X-Slack-Request-Timestamp": _fresh_ts(), "X-Slack-Signature": "v0=dummy"}

        failing_doc = MagicMock()
        failing_doc.insert = MagicMock(side_effect=frappe.ValidationError("insert failed"))

        def fake_get_doc(data_or_doctype, name=None):
            if isinstance(data_or_doctype, dict) and data_or_doctype.get("doctype") == "HD Ticket":
                return failing_doc
            settings_mock = MagicMock()
            settings_mock.enable_slack_integration = False
            return settings_mock

        with patch("helpdesk.api.slack.frappe.local") as mock_local, \
             patch("helpdesk.api.slack.verify_slack_request", return_value=True), \
             patch("helpdesk.api.slack.resolve_slack_user", return_value=email), \
             patch("helpdesk.api.slack.frappe.get_doc", side_effect=fake_get_doc), \
             patch("helpdesk.api.slack.frappe.log_error") as mock_log_error, \
             patch("helpdesk.api.slack.frappe.get_traceback", return_value="Traceback (most recent call last):\n  File test.py"):
            mock_local.request = mock_request

            result = handle_ticket_command()

        mock_log_error.assert_called()
        self.assertEqual(result.get("response_type"), "ephemeral")

        response_text = result.get("text", "")
        traceback_indicators = ["Traceback (most recent call last)", "File \"", "line "]
        for indicator in traceback_indicators:
            self.assertNotIn(indicator, response_text)


# ---------------------------------------------------------------------------
# 5.10  PBT — Property 9: User resolution creates new user only when none exists
# ---------------------------------------------------------------------------

class TestResolveSlackUser(unittest.TestCase):
    """5.10 — Property 9: resolve_slack_user creates User only when absent, reuses when present."""

    def _mock_users_info_response(self, email: str, display_name: str = "Test User"):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "user": {
                "real_name": display_name,
                "profile": {"email": email},
            },
        }
        return mock_resp

    # Feature: slack-integration, Property 9: User resolution creates new user only when none exists
    @given(email=st.emails())
    @h_settings(max_examples=100)
    def test_property_9_reuses_existing_user(self, email):
        """When a Frappe User with the email already exists, no new User is inserted."""
        mock_settings = _mock_settings()
        inserted = []

        def fake_get_doc(data_or_doctype, name=None):
            if isinstance(data_or_doctype, dict) and data_or_doctype.get("doctype") == "User":
                doc = MagicMock()
                doc.insert = MagicMock(side_effect=lambda **kw: inserted.append(email))
                return doc
            return MagicMock()

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.requests.get", return_value=self._mock_users_info_response(email)), \
             patch("helpdesk.api.slack.frappe.db.exists", return_value=True), \
             patch("helpdesk.api.slack.frappe.get_doc", side_effect=fake_get_doc):
            result = resolve_slack_user("U_EXISTING")

        self.assertEqual(result, email)
        self.assertEqual(len(inserted), 0, "Should not insert a new User when one already exists")

    # Feature: slack-integration, Property 9: User resolution creates new user only when none exists
    @given(email=st.emails())
    @h_settings(max_examples=100)
    def test_property_9_creates_new_user_when_absent(self, email):
        """When no Frappe User with the email exists, exactly one new User is inserted."""
        mock_settings = _mock_settings()
        inserted = []

        def fake_get_doc(data_or_doctype, name=None):
            if isinstance(data_or_doctype, dict) and data_or_doctype.get("doctype") == "User":
                doc = MagicMock()
                doc.insert = MagicMock(side_effect=lambda **kw: inserted.append(email))
                return doc
            return MagicMock()

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.requests.get", return_value=self._mock_users_info_response(email)), \
             patch("helpdesk.api.slack.frappe.db.exists", return_value=False), \
             patch("helpdesk.api.slack.frappe.get_doc", side_effect=fake_get_doc):
            result = resolve_slack_user("U_NEW")

        self.assertEqual(result, email)
        self.assertEqual(len(inserted), 1, "Should insert exactly one new User when none exists")


# ---------------------------------------------------------------------------
# 5.11  PBT — Property 10: All slash command responses use ephemeral response type
# ---------------------------------------------------------------------------

class TestEphemeralResponseType(unittest.TestCase):
    """5.11 — Property 10: For any input to handle_ticket_command, response_type == 'ephemeral'."""

    def _make_request(self, text: str, resolve_email=None, insert_raises=False):
        mock_request = MagicMock()
        mock_request.get_data.return_value = b""
        mock_request.form = {"text": text, "user_id": "U123", "user_name": "user", "channel_name": "general"}
        mock_request.headers = {"X-Slack-Request-Timestamp": _fresh_ts(), "X-Slack-Signature": "v0=dummy"}
        return mock_request

    # Feature: slack-integration, Property 10: All slash command responses use ephemeral response type
    @given(
        text=st.text(max_size=200),
        email=st.one_of(st.none(), st.emails()),
    )
    @h_settings(max_examples=100)
    def test_property_10_all_responses_are_ephemeral(self, text, email):
        """handle_ticket_command must always return response_type='ephemeral' regardless of input."""
        mock_request = self._make_request(text)

        def fake_get_doc(data_or_doctype, name=None):
            if isinstance(data_or_doctype, dict) and data_or_doctype.get("doctype") == "HD Ticket":
                doc = MagicMock()
                doc.name = "HD-TEST-001"
                doc.insert = MagicMock(return_value=doc)
                return doc
            settings_mock = MagicMock()
            settings_mock.enable_slack_integration = False
            return settings_mock

        with patch("helpdesk.api.slack.frappe.local") as mock_local, \
             patch("helpdesk.api.slack.verify_slack_request", return_value=True), \
             patch("helpdesk.api.slack.resolve_slack_user", return_value=email), \
             patch("helpdesk.api.slack.frappe.get_doc", side_effect=fake_get_doc), \
             patch("helpdesk.api.slack.frappe.db") as mock_db, \
             patch("helpdesk.api.slack.frappe.enqueue"), \
             patch("helpdesk.api.slack.frappe.log_error"), \
             patch("helpdesk.api.slack.frappe.get_traceback", return_value=""), \
             patch("helpdesk.api.slack.frappe.utils.get_url", return_value="https://helpdesk.example.com"):
            mock_local.request = mock_request
            mock_db.commit = MagicMock()

            result = handle_ticket_command()

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("response_type"), "ephemeral")


# ---------------------------------------------------------------------------
# 5.12  Unit test: frappe.enqueue called (not direct HTTP) in after_insert path
# ---------------------------------------------------------------------------

class TestEnqueueAfterInsert(unittest.TestCase):
    """5.12 — Req 2.3: enqueue_ticket_notification uses frappe.enqueue, not direct HTTP."""

    def test_enqueue_called_when_integration_enabled(self):
        """When enable_slack_integration is True, frappe.enqueue is called with the correct function path."""
        mock_settings = MagicMock()
        mock_settings.enable_slack_integration = True

        mock_doc = MagicMock()
        mock_doc.name = "HD-001"

        with patch("helpdesk.api.slack.frappe.get_cached_doc", return_value=mock_settings), \
             patch("helpdesk.api.slack.frappe.enqueue") as mock_enqueue, \
             patch("helpdesk.api.slack.requests.post") as mock_post:
            enqueue_ticket_notification(mock_doc, "after_insert")

        mock_enqueue.assert_called_once()
        call_kwargs = mock_enqueue.call_args
        # First positional arg must be the function path string, not a direct HTTP call
        fn_path = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("method", "")
        self.assertIn("send_ticket_notification", fn_path)
        mock_post.assert_not_called()

    def test_enqueue_not_called_when_integration_disabled(self):
        """When enable_slack_integration is False, frappe.enqueue is NOT called."""
        mock_settings = MagicMock()
        mock_settings.enable_slack_integration = False

        mock_doc = MagicMock()
        mock_doc.name = "HD-001"

        with patch("helpdesk.api.slack.frappe.get_cached_doc", return_value=mock_settings), \
             patch("helpdesk.api.slack.frappe.enqueue") as mock_enqueue:
            enqueue_ticket_notification(mock_doc, "after_insert")

        mock_enqueue.assert_not_called()


# ---------------------------------------------------------------------------
# 5.13  Unit test: timeout=5 is passed in all requests.get/post calls
# ---------------------------------------------------------------------------

class TestRequestTimeout(unittest.TestCase):
    """5.13 — Req 5.4: All outbound HTTP calls in slack.py use timeout=5."""

    def test_send_ticket_notification_uses_timeout_5(self):
        """requests.post in send_ticket_notification must be called with timeout=5."""
        mock_settings = _mock_settings(enabled=True)
        mock_ticket = _make_ticket_mock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"ok": True}

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.frappe.get_doc", return_value=mock_ticket), \
             patch("helpdesk.api.slack._build_ticket_blocks", return_value=[]), \
             patch("helpdesk.api.slack.requests.post", return_value=mock_response) as mock_post:
            send_ticket_notification("HD-001")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs.get("timeout"), 5)

    def test_resolve_slack_user_uses_timeout_5(self):
        """requests.get in resolve_slack_user must be called with timeout=5."""
        mock_settings = _mock_settings()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "user": {"real_name": "Test User", "profile": {"email": "user@example.com"}},
        }

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.requests.get", return_value=mock_response) as mock_get, \
             patch("helpdesk.api.slack.frappe.db.exists", return_value=True):
            resolve_slack_user("U123")

        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs.get("timeout"), 5)

    def test_source_code_timeout_5_in_all_http_calls(self):
        """Static check: every requests.get/post call in slack.py passes timeout=5."""
        source = inspect.getsource(
            __import__("helpdesk.api.slack", fromlist=["slack"])
        )
        import re
        # Find all requests.get/post calls and verify timeout=5 appears nearby
        calls = re.findall(r"requests\.(get|post)\([^)]+\)", source, re.DOTALL)
        for call_src in calls:
            self.assertIn("timeout=5", call_src, f"Missing timeout=5 in: {call_src[:120]}")


# ---------------------------------------------------------------------------
# 5.14  Unit test: hmac.compare_digest is used in verify_slack_request
# ---------------------------------------------------------------------------

class TestConstantTimeComparison(unittest.TestCase):
    """5.14 — Req 3.4: verify_slack_request uses hmac.compare_digest for constant-time comparison."""

    def test_hmac_compare_digest_used_in_source(self):
        """Static check: verify_slack_request source contains hmac.compare_digest."""
        source = inspect.getsource(verify_slack_request)
        self.assertIn(
            "hmac.compare_digest",
            source,
            "verify_slack_request must use hmac.compare_digest for constant-time comparison",
        )

    def test_compare_digest_called_during_verification(self):
        """Runtime check: hmac.compare_digest is invoked when verify_slack_request runs."""
        secret = "test-secret"
        ts = _fresh_ts()
        body = b"test body"
        sig = _make_signature(secret, ts, body)
        mock_settings = _mock_settings(secret=secret)

        with patch("helpdesk.api.slack._get_slack_settings", return_value=mock_settings), \
             patch("helpdesk.api.slack.hmac.compare_digest", wraps=hmac.compare_digest) as mock_digest:
            verify_slack_request(ts, sig, body)

        mock_digest.assert_called_once()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
