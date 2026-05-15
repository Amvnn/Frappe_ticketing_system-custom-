"""
Google SSO Integration for Frappe Helpdesk

Implements Google OAuth2/OIDC single sign-on. Admins configure credentials and
optional domain restrictions in HD Settings. On first login a Frappe User record
is automatically provisioned with the "Customer" role.

Setup:
1. Create a Google Cloud project and configure an OAuth 2.0 Client ID.
2. Add the Redirect URI (shown in Settings UI) to the authorised redirect URIs.
3. Copy Client ID and Client Secret into HD Settings → Integrations → Google SSO.
"""

import base64
import json
import secrets
import time
from typing import Optional
from urllib.parse import urlencode

import frappe
import requests
from frappe import _


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_google_settings() -> dict:
    """Read Google SSO configuration from HD Settings.

    Returns a dict with keys: google_client_id, google_client_secret,
    google_sso_allowed_domains (list of domain strings).

    Raises frappe.throw (ValidationError) if SSO is disabled or credentials
    are missing — callers should not proceed when this raises.
    """
    settings = frappe.get_cached_doc("HD Settings")

    if not settings.enable_google_sso:
        frappe.throw(
            _("Google SSO is not enabled in HD Settings"),
            frappe.PermissionError,
        )

    client_id = settings.google_client_id
    client_secret = settings.get_password("google_client_secret", raise_exception=False)

    if not client_id:
        frappe.throw(_("Google Client ID is not configured in HD Settings"))

    if not client_secret:
        frappe.throw(_("Google Client Secret is not configured in HD Settings"))

    allowed_domains = [
        row.domain.strip().lower()
        for row in (settings.google_sso_allowed_domains or [])
        if row.domain and row.domain.strip()
    ]

    return {
        "google_client_id": client_id,
        "google_client_secret": client_secret,
        "google_sso_allowed_domains": allowed_domains,
    }


def _get_redirect_uri() -> str:
    """Construct the OAuth2 callback URL from the site's base URL.

    The returned URI must match exactly what is registered in Google Cloud Console.
    """
    base_url = frappe.utils.get_url()
    return f"{base_url}/api/method/helpdesk.api.google_sso.handle_google_callback"


def _is_domain_allowed(email: str, allowed_domains: list) -> bool:
    """Check whether the email's domain is in the allowed domains list.

    Returns True when allowed_domains is empty (open access per Requirement 1.7).
    Comparison is case-insensitive (Requirement 4.5).

    Args:
        email: The authenticated user's email address.
        allowed_domains: List of lowercase domain strings from HD Settings.
    """
    if not allowed_domains:
        return True

    try:
        domain = email.split("@", 1)[1].casefold()
    except IndexError:
        return False

    # Normalise the allowed list with casefold for Unicode-safe case-insensitive comparison
    return domain in [d.casefold() for d in allowed_domains]


def _exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    """Exchange an OAuth2 authorization code for tokens at Google's token endpoint.

    Args:
        code: The authorization code received from Google's redirect.
        redirect_uri: Must match the redirect_uri used in the authorization request.

    Returns:
        The parsed JSON response dict containing at minimum an ``id_token`` key.

    Raises:
        frappe.ValidationError: On network errors, timeouts, or non-2xx responses.
            The Client Secret is never included in logged error messages.
    """
    settings = _get_google_settings()

    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings["google_client_id"],
                "client_secret": settings["google_client_secret"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        frappe.log_error(
            title="Google SSO Token Exchange Timeout",
            message="Request to Google token endpoint timed out after 10 seconds.",
        )
        frappe.throw(_("Google authentication timed out. Please try again."))
    except requests.exceptions.HTTPError as exc:
        # Log status code only — never log the response body which may echo secrets
        frappe.log_error(
            title="Google SSO Token Exchange Failed",
            message=f"Google token endpoint returned HTTP {exc.response.status_code}.",
        )
        frappe.throw(_("Google authentication failed. Please try again."))
    except Exception:
        frappe.log_error(
            title="Google SSO Token Exchange Error",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Google authentication failed. Please try again."))


def _validate_id_token(id_token: str, client_id: str) -> dict:
    """Decode and validate a Google ID token (JWT).

    Performs lightweight validation: decodes the payload segment, verifies the
    ``aud`` claim matches ``client_id``, and checks the ``exp`` claim is in the
    future. Full signature verification against Google's public keys is outside
    scope for this implementation.

    Args:
        id_token: The JWT string returned by Google's token endpoint.
        client_id: The configured OAuth2 Client ID.

    Returns:
        The decoded claims dict on success.

    Raises:
        frappe.ValidationError: If the token is malformed, expired, or the
            audience does not match.
    """
    # JWT structure: header.payload.signature — we only need the payload
    parts = id_token.split(".")
    if len(parts) != 3:
        frappe.throw(_("Invalid ID token format."))

    # Base64url decode with padding correction — only catch actual decode errors
    try:
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        claims = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
    except Exception:
        frappe.log_error(
            title="Google SSO ID Token Decode Error",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Failed to decode Google ID token."))

    # Verify audience matches our client ID (Requirement 3.4)
    if claims.get("aud") != client_id:
        frappe.throw(_("Google ID token audience mismatch."))

    # Verify token is not expired (Requirement 3.4)
    exp = claims.get("exp", 0)
    if int(time.time()) >= exp:
        frappe.throw(_("Google ID token has expired."))

    return claims


# ---------------------------------------------------------------------------
# Public API endpoints
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def initiate_google_oauth() -> dict:
    """Generate and return a Google OAuth2 authorization URL.

    Stores a cryptographically random CSRF state token in the session before
    returning the URL. Returns an error dict if SSO is disabled or misconfigured.

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
    """
    try:
        settings = _get_google_settings()
    except frappe.exceptions.ValidationError as exc:
        return {"error": str(exc)}

    state = secrets.token_urlsafe(32)
    frappe.session.data["google_sso_state"] = state

    redirect_uri = _get_redirect_uri()

    params = {
        "client_id": settings["google_client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

    return {"url": auth_url}


def _provision_user(
    email: str,
    first_name: str,
    last_name: str,
    picture: Optional[str],
) -> str:
    """Find or create a Frappe User from Google identity claims.

    If a User with the given email already exists it is returned unchanged.
    New users are created with the "Customer" role and no welcome email.

    Args:
        email: Authenticated user's email address.
        first_name: Given name from ID token.
        last_name: Family name from ID token.
        picture: Profile picture URL from ID token (may be None).

    Returns:
        The email string (usable as a Frappe User name).

    Raises:
        frappe.ValidationError: On insert failure (after logging the error).

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    if frappe.db.exists("User", email):
        return email

    try:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name or email.split("@")[0],
                "last_name": last_name or "",
                "user_image": picture or "",
                "send_welcome_email": 0,
                "roles": [{"role": "Customer"}],
            }
        )
        user.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="Google SSO User Provisioning Failed",
            message=frappe.get_traceback(),
        )
        frappe.throw(_("Failed to create user account. Please contact your administrator."))

    return email


@frappe.whitelist(allow_guest=True)
def handle_google_callback() -> None:
    """Handle the OAuth2 callback redirect from Google.

    Verifies the CSRF state, exchanges the authorization code for tokens,
    validates the ID token, enforces domain restrictions, provisions the user,
    and establishes a Frappe session before redirecting to /helpdesk.

    On any error the user is redirected to /login with a descriptive message.

    Requirements: 3.1–3.7, 4.1, 4.2, 4.4, 8.4, 8.6
    """
    code = frappe.form_dict.get("code", "")
    state = frappe.form_dict.get("state", "")

    login_url = frappe.utils.get_url("/login")
    helpdesk_url = frappe.utils.get_url("/helpdesk")

    # --- State verification (Requirement 3.2, 8.4) ---
    stored_state = frappe.session.data.get("google_sso_state")
    # Consume immediately regardless of outcome (Requirement 8.4)
    frappe.session.data.pop("google_sso_state", None)

    if not stored_state or not state or state != stored_state:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = login_url + "?sso_error=invalid_state"
        return

    # --- Token exchange (Requirement 3.3) ---
    redirect_uri = _get_redirect_uri()
    try:
        tokens = _exchange_code_for_tokens(code, redirect_uri)
    except Exception:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = login_url + "?sso_error=token_exchange_failed"
        return

    id_token = tokens.get("id_token", "")

    # --- ID token validation (Requirements 3.4, 3.5) ---
    try:
        settings = _get_google_settings()
        claims = _validate_id_token(id_token, settings["google_client_id"])
    except Exception:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = login_url + "?sso_error=token_validation_failed"
        return

    # --- Extract identity claims (Requirement 3.6) ---
    email = claims.get("email", "")
    first_name = claims.get("given_name", "")
    last_name = claims.get("family_name", "")
    picture = claims.get("picture", "")

    if not email:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = login_url + "?sso_error=missing_email"
        return

    # --- Domain restriction (Requirements 4.1, 4.2, 8.6) ---
    allowed_domains = settings.get("google_sso_allowed_domains", [])
    if not _is_domain_allowed(email, allowed_domains):
        rejected_domain = email.split("@", 1)[1] if "@" in email else email
        frappe.log_error(
            title="Google SSO Domain Rejected",
            message=f"Login rejected for domain: {rejected_domain}",
        )
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = login_url + "?sso_error=domain_not_allowed"
        return

    # --- User provisioning (Requirements 5.1–5.5) ---
    try:
        email = _provision_user(email, first_name, last_name, picture)
    except Exception:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = login_url + "?sso_error=user_provisioning_failed"
        return

    # --- Establish session and redirect (Requirement 3.7) ---
    frappe.local.login_manager.login_as(email)
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = helpdesk_url


def get_login_page_context() -> dict:
    """Return context for the Frappe login page template.

    Called via the ``login_page_fields`` hook in hooks.py.
    Returns ``show_google_sso: True`` only when the toggle is enabled.

    Requirements: 6.1, 6.3
    """
    try:
        settings = frappe.get_cached_doc("HD Settings")
        return {"show_google_sso": bool(settings.enable_google_sso)}
    except Exception:
        return {"show_google_sso": False}


def inject_login_context(context):
    """Inject show_google_sso into every website page context.
    Called via the website_context hook — this is the correct Frappe v15 hook
    for injecting context into Jinja-rendered pages including /login.
    """
    try:
        settings = frappe.get_cached_doc("HD Settings")
        context["show_google_sso"] = bool(settings.enable_google_sso)
    except Exception:
        context["show_google_sso"] = False
