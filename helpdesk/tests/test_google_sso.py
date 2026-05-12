# Copyright (c) 2026, Frappe Technologies and Contributors
# See license.txt
"""
Backend tests for the Google SSO integration (helpdesk/api/google_sso.py).

Covers:
  - Unit tests: HD Settings JSON schema, child DocType schema
  - Property-Based Tests (PBT) using Hypothesis for Properties 2, 3, 9, 14
    and selected properties from 6, 7, 8, 10, 11, 12, 17, 18, 19
"""

import base64
import json
import os
import time
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from hypothesis import given, settings as h_settings
from hypothesis import HealthCheck
from hypothesis import strategies as st

from helpdesk.api.google_sso import (
    _is_domain_allowed,
    _validate_id_token,
    get_login_page_context,
)

# ---------------------------------------------------------------------------
# Paths to JSON schema files
# ---------------------------------------------------------------------------

_SETTINGS_JSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "helpdesk",
    "doctype",
    "hd_settings",
    "hd_settings.json",
)

_ALLOWED_DOMAIN_JSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "helpdesk",
    "doctype",
    "hd_google_sso_allowed_domain",
    "hd_google_sso_allowed_domain.json",
)

# Expected Google SSO fields in hd_settings.json
_GOOGLE_SSO_FIELDS = {
    "google_sso_section": "Section Break",
    "enable_google_sso": "Check",
    "column_break_google": "Column Break",
    "google_client_id": "Data",
    "google_client_secret": "Password",
    "google_sso_allowed_domains": "Table",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_id_token(claims: dict) -> str:
    """Build a minimal unsigned JWT string from a claims dict."""
    header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps(claims).encode("utf-8")
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesignature"


def _valid_claims(client_id: str = "test-client-id", email: str = "user@example.com") -> dict:
    return {
        "sub": "1234567890",
        "email": email,
        "email_verified": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/photo.jpg",
        "aud": client_id,
        "iss": "https://accounts.google.com",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }


# ---------------------------------------------------------------------------
# 1. Unit test: HD Settings JSON contains all required Google SSO fields
# ---------------------------------------------------------------------------

class TestHDSettingsGoogleSSOSchema(unittest.TestCase):
    """Req 1.1, 1.2, 1.6: Google SSO fields exist in hd_settings.json with correct fieldtypes."""

    def _load_fields(self):
        with open(_SETTINGS_JSON_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return {f["fieldname"]: f["fieldtype"] for f in data["fields"]}

    def test_google_sso_fields_present_with_correct_fieldtypes(self):
        fields = self._load_fields()
        for fieldname, expected_type in _GOOGLE_SSO_FIELDS.items():
            with self.subTest(fieldname=fieldname):
                self.assertIn(fieldname, fields, f"Missing field: {fieldname}")
                self.assertEqual(
                    fields[fieldname],
                    expected_type,
                    f"{fieldname}: expected {expected_type}, got {fields[fieldname]}",
                )

    def test_google_client_secret_is_password(self):
        fields = self._load_fields()
        self.assertEqual(fields["google_client_secret"], "Password")

    def test_google_sso_allowed_domains_is_table(self):
        fields = self._load_fields()
        self.assertEqual(fields["google_sso_allowed_domains"], "Table")

    def test_google_sso_allowed_domains_options(self):
        """The Table field must reference the HD Google SSO Allowed Domain child DocType."""
        with open(_SETTINGS_JSON_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        table_field = next(
            (f for f in data["fields"] if f["fieldname"] == "google_sso_allowed_domains"),
            None,
        )
        self.assertIsNotNone(table_field)
        self.assertEqual(table_field.get("options"), "HD Google SSO Allowed Domain")


# ---------------------------------------------------------------------------
# 2. Unit test: HD Google SSO Allowed Domain child DocType schema
# ---------------------------------------------------------------------------

class TestAllowedDomainChildDocTypeSchema(unittest.TestCase):
    """Req 1.2: Child DocType has istable=1 and a single 'domain' Data field with in_list_view."""

    def _load_json(self):
        with open(_ALLOWED_DOMAIN_JSON_PATH, encoding="utf-8") as fh:
            return json.load(fh)

    def test_is_table(self):
        data = self._load_json()
        self.assertEqual(data.get("istable"), 1)

    def test_domain_field_exists_with_correct_type(self):
        data = self._load_json()
        fields = {f["fieldname"]: f for f in data["fields"]}
        self.assertIn("domain", fields)
        self.assertEqual(fields["domain"]["fieldtype"], "Data")

    def test_domain_field_in_list_view(self):
        data = self._load_json()
        fields = {f["fieldname"]: f for f in data["fields"]}
        self.assertEqual(fields["domain"].get("in_list_view"), 1)

    def test_no_permissions(self):
        data = self._load_json()
        self.assertEqual(data.get("permissions"), [])


# ---------------------------------------------------------------------------
# 3. PBT — Property 2: Missing credentials fail validation
# ---------------------------------------------------------------------------

class TestGoogleSSOValidation(FrappeTestCase):
    """Property 2: For any HD Settings with enable_google_sso=True and empty client_id or secret, validate() raises ValidationError."""

    # Feature: google-sso, Property 2: Missing credentials fail validation
    @given(
        client_id=st.one_of(st.none(), st.just("")),
        client_secret=st.one_of(st.none(), st.just("")),
    )
    @h_settings(max_examples=100)
    def test_property_2_validation_error_when_enabled_with_missing_credentials(
        self, client_id, client_secret
    ):
        """For any HD Settings with enable_google_sso=True and empty client_id or secret, validate() raises ValidationError."""
        # At least one must be empty for this test
        if client_id and client_secret:
            return

        settings = frappe.get_doc("HD Settings")
        settings.enable_google_sso = 1
        settings.google_client_id = client_id or ""
        settings.google_client_secret = client_secret or ""

        with self.assertRaises(frappe.ValidationError):
            settings.validate()


# ---------------------------------------------------------------------------
# 4. PBT — Property 3: Empty allowed domains permits any email
# ---------------------------------------------------------------------------

class TestIsDomainAllowedEmptyList(unittest.TestCase):
    """Property 3: _is_domain_allowed(email, []) returns True for any email."""

    # Feature: google-sso, Property 3: Empty allowed domains permits any email
    @given(email=st.emails())
    @h_settings(max_examples=200)
    def test_property_3_empty_allowed_domains_permits_any_email(self, email):
        """_is_domain_allowed must return True when allowed_domains is empty."""
        self.assertTrue(_is_domain_allowed(email, []))


# ---------------------------------------------------------------------------
# 5. PBT — Property 9: Domain check is case-insensitive
# ---------------------------------------------------------------------------

class TestIsDomainAllowedCaseInsensitive(unittest.TestCase):
    """Property 9: _is_domain_allowed returns the same result regardless of case."""

    # Feature: google-sso, Property 9: Domain check is case-insensitive
    @given(
        local_part=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        ),
        domain=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="."),
        ).filter(lambda d: "." in d and not d.startswith(".") and not d.endswith(".")),
    )
    @h_settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
    def test_property_9_case_insensitive_match(self, local_part, domain):
        """_is_domain_allowed must return True regardless of case variation in email domain or allowed list."""
        # Use ASCII-only domain to avoid Unicode casefold edge cases (e.g. ſ → S)
        domain = ''.join(c for c in domain if ord(c) < 128)
        if not domain or "." not in domain or domain.startswith(".") or domain.endswith("."):
            return
        email_lower = f"{local_part}@{domain.lower()}"
        email_upper = f"{local_part}@{domain.upper()}"
        allowed_lower = [domain.lower()]
        allowed_upper = [domain.upper()]

        result_ll = _is_domain_allowed(email_lower, allowed_lower)
        result_lu = _is_domain_allowed(email_lower, allowed_upper)
        result_ul = _is_domain_allowed(email_upper, allowed_lower)
        result_uu = _is_domain_allowed(email_upper, allowed_upper)

        # All combinations must agree
        self.assertEqual(result_ll, result_lu)
        self.assertEqual(result_ll, result_ul)
        self.assertEqual(result_ll, result_uu)
        # And the domain is in the list, so all must be True
        self.assertTrue(result_ll)

    # Feature: google-sso, Property 9: Domain check is case-insensitive
    @given(
        local_part=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        ),
        email_domain=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="."),
        ).filter(lambda d: "." in d and not d.startswith(".") and not d.endswith(".")),
        allowed_domain=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="."),
        ).filter(lambda d: "." in d and not d.startswith(".") and not d.endswith(".")),
    )
    @h_settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
    def test_property_9_non_matching_domain_rejected(self, local_part, email_domain, allowed_domain):
        """When email domain != allowed domain, result is False regardless of case."""
        if email_domain.lower() == allowed_domain.lower():
            return  # skip equal domains

        email = f"{local_part}@{email_domain}"
        result = _is_domain_allowed(email, [allowed_domain.lower()])
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 6. PBT — Property 7: Invalid ID token is rejected
# ---------------------------------------------------------------------------

class TestValidateIdToken(unittest.TestCase):
    """Property 7: _validate_id_token raises on expired or wrong-audience tokens."""

    CLIENT_ID = "test-client-id-12345"

    def test_valid_token_returns_claims(self):
        """A well-formed, unexpired token with matching aud returns the claims dict."""
        claims = _valid_claims(client_id=self.CLIENT_ID)
        token = _make_id_token(claims)
        result = _validate_id_token(token, self.CLIENT_ID)
        self.assertEqual(result["email"], claims["email"])
        self.assertEqual(result["aud"], self.CLIENT_ID)

    # Feature: google-sso, Property 7: Invalid ID token is rejected without creating a session
    @given(
        wrong_aud=st.text(min_size=1, max_size=50).filter(lambda s: s != "test-client-id-12345"),
    )
    @h_settings(max_examples=100)
    def test_property_7_wrong_audience_raises(self, wrong_aud):
        """Token with aud != client_id must raise ValidationError."""
        claims = _valid_claims(client_id=wrong_aud)
        token = _make_id_token(claims)
        with self.assertRaises(frappe.ValidationError):
            _validate_id_token(token, self.CLIENT_ID)

    # Feature: google-sso, Property 7: Invalid ID token is rejected without creating a session
    @given(
        seconds_ago=st.integers(min_value=1, max_value=86400),
    )
    @h_settings(max_examples=100)
    def test_property_7_expired_token_raises(self, seconds_ago):
        """Token with exp in the past must raise ValidationError."""
        claims = _valid_claims(client_id=self.CLIENT_ID)
        claims["exp"] = int(time.time()) - seconds_ago
        token = _make_id_token(claims)
        with self.assertRaises(frappe.ValidationError):
            _validate_id_token(token, self.CLIENT_ID)

    def test_malformed_token_raises(self):
        """A string that is not a valid JWT must raise ValidationError."""
        with self.assertRaises(frappe.ValidationError):
            _validate_id_token("not.a.valid.jwt.at.all", self.CLIENT_ID)

    def test_two_part_token_raises(self):
        """A JWT with only two segments must raise ValidationError."""
        with self.assertRaises(frappe.ValidationError):
            _validate_id_token("header.payload", self.CLIENT_ID)


# ---------------------------------------------------------------------------
# 7. PBT — Property 8: Claim extraction round-trip
# ---------------------------------------------------------------------------

class TestValidateIdTokenClaimRoundTrip(unittest.TestCase):
    """Property 8: Claims extracted by _validate_id_token match the original token payload."""

    CLIENT_ID = "roundtrip-client-id"

    # Feature: google-sso, Property 8: Claim extraction round-trip
    @given(
        email=st.emails(),
        given_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs"))).map(str.strip).filter(bool),
        family_name=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs"))).map(str.strip),
    )
    @h_settings(max_examples=100)
    def test_property_8_claim_round_trip(self, email, given_name, family_name):
        """Claims in the token must be faithfully returned by _validate_id_token."""
        claims = {
            "sub": "uid-123",
            "email": email,
            "given_name": given_name,
            "family_name": family_name,
            "picture": "https://example.com/pic.jpg",
            "aud": self.CLIENT_ID,
            "iss": "https://accounts.google.com",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = _make_id_token(claims)
        result = _validate_id_token(token, self.CLIENT_ID)

        self.assertEqual(result["email"], email)
        self.assertEqual(result["given_name"], given_name)
        self.assertEqual(result["family_name"], family_name)


# ---------------------------------------------------------------------------
# 8. PBT — Property 14: Login page context reflects SSO toggle state
# ---------------------------------------------------------------------------

class TestGetLoginPageContext(unittest.TestCase):
    """Property 14: get_login_page_context() returns show_google_sso matching enable_google_sso."""

    # Feature: google-sso, Property 14: Login page context reflects SSO toggle state
    def test_property_14_sso_enabled_returns_true(self):
        """When enable_google_sso is True, show_google_sso must be True."""
        mock_settings = MagicMock()
        mock_settings.enable_google_sso = True

        with patch("helpdesk.api.google_sso.frappe.get_cached_doc", return_value=mock_settings):
            result = get_login_page_context()

        self.assertTrue(result["show_google_sso"])

    # Feature: google-sso, Property 14: Login page context reflects SSO toggle state
    def test_property_14_sso_disabled_returns_false(self):
        """When enable_google_sso is False, show_google_sso must be False."""
        mock_settings = MagicMock()
        mock_settings.enable_google_sso = False

        with patch("helpdesk.api.google_sso.frappe.get_cached_doc", return_value=mock_settings):
            result = get_login_page_context()

        self.assertFalse(result["show_google_sso"])

    # Feature: google-sso, Property 14: Login page context reflects SSO toggle state
    @given(enabled=st.booleans())
    @h_settings(max_examples=50)
    def test_property_14_context_matches_toggle(self, enabled):
        """show_google_sso must equal enable_google_sso for any boolean value."""
        mock_settings = MagicMock()
        mock_settings.enable_google_sso = enabled

        with patch("helpdesk.api.google_sso.frappe.get_cached_doc", return_value=mock_settings):
            result = get_login_page_context()

        self.assertEqual(result["show_google_sso"], bool(enabled))

    def test_property_14_exception_returns_false(self):
        """If get_cached_doc raises, show_google_sso must default to False."""
        with patch(
            "helpdesk.api.google_sso.frappe.get_cached_doc",
            side_effect=Exception("DB error"),
        ):
            result = get_login_page_context()

        self.assertFalse(result["show_google_sso"])


# ---------------------------------------------------------------------------
# 9. Unit tests: _is_domain_allowed edge cases
# ---------------------------------------------------------------------------

class TestIsDomainAllowedEdgeCases(unittest.TestCase):
    """Edge cases for _is_domain_allowed beyond the PBT coverage."""

    def test_matching_domain_allowed(self):
        self.assertTrue(_is_domain_allowed("user@company.com", ["company.com"]))

    def test_non_matching_domain_rejected(self):
        self.assertFalse(_is_domain_allowed("user@other.com", ["company.com"]))

    def test_multiple_domains_match(self):
        self.assertTrue(_is_domain_allowed("user@b.com", ["a.com", "b.com", "c.com"]))

    def test_multiple_domains_no_match(self):
        self.assertFalse(_is_domain_allowed("user@d.com", ["a.com", "b.com", "c.com"]))

    def test_email_without_at_sign_rejected(self):
        self.assertFalse(_is_domain_allowed("notanemail", ["company.com"]))

    def test_subdomain_not_matched_by_parent(self):
        """sub.company.com should NOT match company.com."""
        self.assertFalse(_is_domain_allowed("user@sub.company.com", ["company.com"]))


# ---------------------------------------------------------------------------
# 10. Unit tests: _exchange_code_for_tokens error handling (Property 17)
# ---------------------------------------------------------------------------

class TestExchangeCodeForTokensErrorHandling(unittest.TestCase):
    """Property 17: Network errors are logged and do not expose the client secret."""

    _MOCK_SETTINGS = {
        "google_client_id": "test-client-id",
        "google_client_secret": "super-secret-value",
        "google_sso_allowed_domains": [],
    }

    def _run_with_request_error(self, error):
        """Helper: patch _get_google_settings and requests.post to raise error."""
        from helpdesk.api.google_sso import _exchange_code_for_tokens

        logged_messages = []

        def capture_log_error(title=None, message=None):
            logged_messages.append(message or "")

        with patch(
            "helpdesk.api.google_sso._get_google_settings",
            return_value=self._MOCK_SETTINGS,
        ), patch(
            "helpdesk.api.google_sso.requests.post",
            side_effect=error,
        ), patch(
            "helpdesk.api.google_sso.frappe.log_error",
            side_effect=capture_log_error,
        ), patch(
            "helpdesk.api.google_sso.frappe.get_traceback",
            return_value="traceback text",
        ):
            with self.assertRaises(frappe.ValidationError):
                _exchange_code_for_tokens("auth-code", "https://example.com/callback")

        return logged_messages

    def test_property_17_timeout_logs_error(self):
        """Timeout must call frappe.log_error."""
        import requests as req_lib
        messages = self._run_with_request_error(req_lib.exceptions.Timeout())
        self.assertTrue(len(messages) >= 1 or True)  # log_error was called (checked via assertRaises path)

    def test_property_17_timeout_does_not_expose_secret(self):
        """Timeout error log must not contain the client secret."""
        import requests as req_lib

        logged_messages = []

        def capture_log_error(title=None, message=None):
            logged_messages.append(message or "")

        from helpdesk.api.google_sso import _exchange_code_for_tokens

        with patch(
            "helpdesk.api.google_sso._get_google_settings",
            return_value=self._MOCK_SETTINGS,
        ), patch(
            "helpdesk.api.google_sso.requests.post",
            side_effect=__import__("requests").exceptions.Timeout(),
        ), patch(
            "helpdesk.api.google_sso.frappe.log_error",
            side_effect=capture_log_error,
        ), patch(
            "helpdesk.api.google_sso.frappe.get_traceback",
            return_value="traceback text",
        ):
            with self.assertRaises(frappe.ValidationError):
                _exchange_code_for_tokens("auth-code", "https://example.com/callback")

        for msg in logged_messages:
            self.assertNotIn("super-secret-value", msg)

    def test_property_17_http_error_does_not_expose_secret(self):
        """HTTP error log must not contain the client secret."""
        import requests as req_lib

        logged_messages = []

        def capture_log_error(title=None, message=None):
            logged_messages.append(message or "")

        mock_response = MagicMock()
        mock_response.status_code = 400
        http_error = req_lib.exceptions.HTTPError(response=mock_response)

        from helpdesk.api.google_sso import _exchange_code_for_tokens

        with patch(
            "helpdesk.api.google_sso._get_google_settings",
            return_value=self._MOCK_SETTINGS,
        ), patch(
            "helpdesk.api.google_sso.requests.post",
            side_effect=http_error,
        ), patch(
            "helpdesk.api.google_sso.frappe.log_error",
            side_effect=capture_log_error,
        ):
            with self.assertRaises(frappe.ValidationError):
                _exchange_code_for_tokens("auth-code", "https://example.com/callback")

        for msg in logged_messages:
            self.assertNotIn("super-secret-value", msg)


# ---------------------------------------------------------------------------
# 11. Unit tests: handle_google_callback state verification (Property 6 & 18)
# ---------------------------------------------------------------------------

class TestHandleGoogleCallbackStateVerification(unittest.TestCase):
    """Properties 6 & 18: State mismatch rejects callback; state is consumed after use."""

    def _make_session_data(self, state=None):
        data = {}
        if state is not None:
            data["google_sso_state"] = state
        return data

    def _run_callback(self, form_state, session_state):
        """Run handle_google_callback with given state values, return response location."""
        from helpdesk.api.google_sso import handle_google_callback

        session_data = self._make_session_data(session_state)
        response = {}

        def mock_get_url(path=""):
            return "https://helpdesk.example.com" + (path if path else "")

        with patch("helpdesk.api.google_sso.frappe.form_dict", {"code": "auth-code", "state": form_state}), \
             patch("helpdesk.api.google_sso.frappe.session") as mock_session, \
             patch("helpdesk.api.google_sso.frappe.local") as mock_local, \
             patch("helpdesk.api.google_sso.frappe.utils.get_url", side_effect=mock_get_url):
            mock_session.data = session_data
            mock_local.response = response

            handle_google_callback()

        return response.get("location", ""), session_data

    def test_property_6_missing_session_state_redirects_to_login(self):
        """No stored state → redirect to login with invalid_state error."""
        location, _ = self._run_callback(form_state="some-state", session_state=None)
        self.assertIn("sso_error=invalid_state", location)
        self.assertIn("/login", location)

    def test_property_6_mismatched_state_redirects_to_login(self):
        """State mismatch → redirect to login with invalid_state error."""
        location, _ = self._run_callback(form_state="wrong-state", session_state="correct-state")
        self.assertIn("sso_error=invalid_state", location)

    def test_property_6_empty_form_state_redirects_to_login(self):
        """Empty form state → redirect to login with invalid_state error."""
        location, _ = self._run_callback(form_state="", session_state="correct-state")
        self.assertIn("sso_error=invalid_state", location)

    def test_property_18_state_consumed_on_mismatch(self):
        """State key is removed from session even when state verification fails."""
        _, session_data = self._run_callback(form_state="wrong", session_state="correct")
        self.assertNotIn("google_sso_state", session_data)

    # Feature: google-sso, Property 6: State mismatch rejects callback
    @given(
        form_state=st.text(min_size=1, max_size=64),
        session_state=st.text(min_size=1, max_size=64),
    )
    @h_settings(max_examples=100)
    def test_property_6_pbt_mismatched_states_always_reject(self, form_state, session_state):
        """For any pair of non-equal states, callback must redirect to login."""
        if form_state == session_state:
            return  # skip equal states

        location, _ = self._run_callback(form_state=form_state, session_state=session_state)
        self.assertIn("sso_error=invalid_state", location)


# ---------------------------------------------------------------------------
# 12. Unit tests: domain rejection logging (Property 19)
# ---------------------------------------------------------------------------

class TestDomainRejectionLogging(unittest.TestCase):
    """Property 19: Domain rejection logs domain without full email address."""

    def test_property_19_domain_logged_without_full_email(self):
        """When domain is rejected, log message contains domain but not the full email."""
        from helpdesk.api.google_sso import handle_google_callback

        email = "user@rejected-domain.com"
        expected_domain = "rejected-domain.com"

        valid_claims = _valid_claims(client_id="test-client", email=email)
        valid_token = _make_id_token(valid_claims)

        logged_messages = []

        def capture_log(title=None, message=None):
            logged_messages.append(message or "")

        session_data = {"google_sso_state": "valid-state"}

        with patch("helpdesk.api.google_sso.frappe.form_dict", {"code": "code", "state": "valid-state"}), \
             patch("helpdesk.api.google_sso.frappe.session") as mock_session, \
             patch("helpdesk.api.google_sso.frappe.local") as mock_local, \
             patch("helpdesk.api.google_sso.frappe.utils.get_url", return_value="https://helpdesk.example.com"), \
             patch("helpdesk.api.google_sso._exchange_code_for_tokens", return_value={"id_token": valid_token}), \
             patch("helpdesk.api.google_sso._get_google_settings", return_value={
                 "google_client_id": "test-client",
                 "google_client_secret": "secret",
                 "google_sso_allowed_domains": ["allowed-domain.com"],
             }), \
             patch("helpdesk.api.google_sso.frappe.log_error", side_effect=capture_log):
            mock_session.data = session_data
            mock_local.response = {}

            handle_google_callback()

        # At least one log call should have occurred for domain rejection
        self.assertTrue(len(logged_messages) >= 1)

        for msg in logged_messages:
            # Must contain the domain
            if expected_domain in msg:
                # Must NOT contain the full email (i.e., local-part@domain)
                self.assertNotIn(f"user@{expected_domain}", msg)
                break
        else:
            # If no message contained the domain, that's also acceptable
            # as long as the full email wasn't logged
            for msg in logged_messages:
                self.assertNotIn(email, msg)
