# Design Document: Google SSO Integration

## Overview

This document describes the technical design for adding Google SSO (Single Sign-On) to Frappe Helpdesk. The feature enables users to authenticate via Google OAuth2/OIDC using their company Google Workspace account, with optional domain restrictions to limit access to specific email domains (e.g., `@company.com`).

The integration follows the same architectural patterns as the existing Slack integration:
- Configuration stored in HD Settings (singleton DocType)
- Settings UI in the Integrations tab
- Backend API endpoints for OAuth2 flow
- Automatic user provisioning on first login

When a user signs in with Google for the first time, a Frappe User record is automatically created. Subsequent logins reuse the existing record. The feature coexists with username/password authentication — both methods remain available simultaneously.

---

## Architecture

```mermaid
graph TD
    subgraph Browser
        A[User] -->|clicks Sign in with Google| B[Login Page]
        B -->|redirects to| C[Google Authorization]
        C -->|redirects back with code| D[OAuth2 Callback]
    end

    subgraph Frappe Backend
        E[initiate_google_oauth API] -->|generates auth URL| B
        E -->|stores state in session| F[Session Store]
        
        D -->|calls| G[handle_google_callback API]
        G -->|verifies state| F
        G -->|exchanges code for tokens| H[Google Token Endpoint]
        H -->|returns ID token| G
        G -->|validates & extracts claims| I[ID Token Validator]
        I -->|checks domain| J{Domain Allowed?}
        J -->|No| K[Redirect to login with error]
        J -->|Yes| L[User Provisioner]
        L -->|finds or creates| M[Frappe User]
        M -->|establishes session| N[frappe.local.login_manager]
        N -->|redirects to| O[Helpdesk Home]
    end

    subgraph HD Settings
        P[enable_google_sso Check]
        Q[google_client_id Data]
        R[google_client_secret Password]
        S[google_sso_allowed_domains Child Table]
    end

    E --> P
    E --> Q
    E --> R
    G --> P
    G --> Q
    G --> R
    J --> S

### Key Design Decisions

- **Custom OAuth2 flow, not Frappe's built-in Social Login**: Frappe has a built-in Social Login feature, but it requires configuration through the Frappe Desk UI and does not support per-integration domain restrictions stored in HD Settings. A custom implementation gives full control over the flow and keeps all configuration in HD Settings, consistent with the Slack integration pattern.

- **Redirect-based callback, not a JSON API**: The OAuth2 callback endpoint performs a browser redirect (HTTP 302) rather than returning JSON. This is required because Google redirects the user's browser to the callback URL — the response must be a redirect, not a JSON payload.

- **State parameter stored in Frappe session**: The CSRF state token is stored in `frappe.session.data` (server-side session), not in a cookie or URL parameter, to prevent CSRF attacks. It is consumed and deleted immediately after verification.

- **`requests` library for token exchange**: The existing codebase uses `requests` for outbound HTTP (see `slack.py`). The same library is used here for consistency. A 10-second timeout is applied to all outbound calls per Requirement 8.2.

- **Child DocType for allowed domains**: A new `HD Google SSO Allowed Domain` child DocType stores the domain list. This follows the same pattern as `HD Team Member` and allows the list to be managed via the standard Frappe child table UI.

- **User provisioned with "Customer" role**: New users created via Google SSO are given the "Customer" role (Requirement 5.4), directing them to the customer portal rather than the agent desk. This matches the expected use case for external users authenticating via Google Workspace.

- **Login page button via Frappe `login_page_fields` hook**: Frappe exposes a `login_page_fields` hook that allows apps to inject additional context into the `/login` page template. The Google SSO button is injected via this mechanism, keeping the implementation within the Frappe extension model without patching core templates.

---

## Components and Interfaces

### Backend: `helpdesk/api/google_sso.py` (new file)

Contains all OAuth2 flow logic.

```
initiate_google_oauth()          — @frappe.whitelist(allow_guest=True)
                                   Generates and returns the Google authorization URL.
                                   Stores state in session. Returns error if SSO disabled.

handle_google_callback()         — @frappe.whitelist(allow_guest=True)
                                   Accepts code + state from Google redirect.
                                   Verifies state, exchanges code, validates ID token,
                                   enforces domain restriction, provisions user,
                                   establishes session, redirects to /helpdesk.

_get_google_settings() -> dict   — Reads HD Settings fields; raises if not configured.

_exchange_code_for_tokens(code, redirect_uri) -> dict
                                 — POSTs to Google token endpoint; returns token dict.

_validate_id_token(id_token, client_id) -> dict
                                 — Validates JWT signature, aud, exp claims.
                                   Returns decoded claims dict.

_is_domain_allowed(email, allowed_domains) -> bool
                                 — Case-insensitive domain check against allowed list.
                                   Returns True if list is empty (open access).

_provision_user(email, first_name, last_name, picture) -> str
                                 — Finds or creates Frappe User. Returns email.

_get_redirect_uri() -> str       — Constructs callback URL from site base URL.
```

### Backend: HD Settings DocType changes

New fields added to `hd_settings.json` under the existing `integrations_tab`:

| fieldname | fieldtype | label |
|---|---|---|
| `google_sso_section` | Section Break | Google SSO |
| `enable_google_sso` | Check | Enable Google SSO |
| `column_break_google` | Column Break | — |
| `google_client_id` | Data | Google Client ID |
| `google_client_secret` | Password | Google Client Secret |
| `google_sso_allowed_domains` | Table | Google SSO Allowed Domains (options: HD Google SSO Allowed Domain) |

Validation in `hd_settings.py`: when `enable_google_sso` is checked, both `google_client_id` and `google_client_secret` must be non-empty (mirrors `validate_slack_settings` pattern).

### Backend: `HD Google SSO Allowed Domain` child DocType (new)

A minimal child DocType with a single `domain` field (Data type, `in_list_view: 1`). Stored in `helpdesk/helpdesk/doctype/hd_google_sso_allowed_domain/`.

### Backend: `helpdesk/auth.py` changes

Add the two new Google SSO endpoints to `ALLOWED_PATHS` so they are accessible to Guest users:

```python
"/api/method/helpdesk.api.google_sso.initiate_google_oauth",
"/api/method/helpdesk.api.google_sso.handle_google_callback",
```

### Backend: `helpdesk/hooks.py` changes

Add a `login_page_fields` hook to inject the Google SSO button context into the Frappe login page:

```python
login_page_fields = "helpdesk.api.google_sso.get_login_page_context"
```

`get_login_page_context()` returns a dict with `show_google_sso: bool` that the login page template uses to conditionally render the button.

### Frontend: `desk/src/components/Settings/GoogleSSO/GoogleSSOSettings.vue` (new)

New Vue component following the same pattern as `SlackSettings.vue`:

- Uses `createResource` on `frappe.client.get` / `frappe.client.set_value` for HD Settings
- Renders a toggle (Switch), Client ID text input, Client Secret password input, Allowed Domains list, and a read-only Redirect URI field
- Disables/greys credential fields when the toggle is off
- Shows "Unsaved" badge and Save button when dirty
- Read-only for non-manager roles

### Frontend: `desk/src/components/Settings/settingsModal.ts` changes

Add a new item to the "Integrations" tab group:

```typescript
{
  label: __("Google SSO"),
  icon: markRaw(LucideKeyRound),
  component: markRaw(GoogleSSOSettings),
  condition: () => auth.isAdmin || auth.isManager,
}
```

### Frontend: Login Page Button

The Frappe `/login` page is a Jinja-rendered HTML page. The `login_page_fields` hook injects `show_google_sso` into the template context. A custom `login.html` override in `helpdesk/templates/` renders the "Sign in with Google" button when `show_google_sso` is true.

The button calls `initiate_google_oauth` via a simple `<a href>` or a small inline script that fetches the URL and redirects.

---

## Data Models

### HD Settings — new fields (additions to existing singleton)

```
enable_google_sso          : Check (default 0)
google_client_id           : Data
google_client_secret       : Password
google_sso_allowed_domains : Table → HD Google SSO Allowed Domain
```

### HD Google SSO Allowed Domain — new child DocType

```
domain : Data (in_list_view: 1, e.g. "company.com")
```

`istable: 1`, no permissions (inherits from parent).

### OAuth2 State — session storage

Stored in `frappe.session.data["google_sso_state"]` as a string. Deleted immediately after consumption in the callback.

### Google ID Token claims (decoded JWT payload)

```json
{
  "sub":            "<google-user-id>",
  "email":          "user@company.com",
  "email_verified": true,
  "name":           "Full Name",
  "given_name":     "First",
  "family_name":    "Last",
  "picture":        "https://...",
  "aud":            "<client_id>",
  "iss":            "https://accounts.google.com",
  "exp":            1234567890,
  "iat":            1234567890
}
```

### Frappe User record created by User_Provisioner

```
doctype:           "User"
email:             <email claim>
first_name:        <given_name claim>
last_name:         <family_name claim>
user_image:        <picture claim>
send_welcome_email: 0
roles:             [{"role": "Customer"}]
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Disabled SSO blocks all flows

*For any* call to `initiate_google_oauth` or `handle_google_callback` when `enable_google_sso` is `False` in HD Settings, the handler shall return an error response and shall make zero outbound HTTP calls to Google APIs.

**Validates: Requirements 1.3, 2.4**

---

### Property 2: Missing credentials fail validation

*For any* HD Settings document where `enable_google_sso` is `True` and either `google_client_id` or `google_client_secret` is empty, calling `validate()` shall raise a `frappe.ValidationError` and prevent the document from being saved.

**Validates: Requirements 1.4, 1.5**

---

### Property 3: Empty allowed domains permits any email

*For any* email address, when `_is_domain_allowed(email, [])` is called with an empty allowed domains list, it shall return `True`.

**Validates: Requirements 1.7, 4.3**

---

### Property 4: Authorization URL contains all required OAuth2 parameters

*For any* valid Google SSO configuration (non-empty client ID, secret, and SSO enabled), calling `initiate_google_oauth` shall return a URL that contains all of: `client_id`, `redirect_uri`, `response_type=code`, `scope` containing `openid`, `email`, and `profile`, and `access_type=offline`.

**Validates: Requirements 2.2**

---

### Property 5: State is stored in session and included in authorization URL

*For any* call to `initiate_google_oauth` that succeeds, the returned authorization URL shall contain a `state` parameter whose value equals the value stored in `frappe.session.data["google_sso_state"]`.

**Validates: Requirements 2.3**

---

### Property 6: State mismatch rejects callback

*For any* call to `handle_google_callback` where the `state` parameter does not match the value stored in the session (including missing, empty, or tampered values), the handler shall reject the request and shall not proceed to token exchange or user provisioning.

**Validates: Requirements 3.2**

---

### Property 7: Invalid ID token is rejected without creating a session

*For any* ID token where the `aud` claim does not match the configured Client ID, or where the `exp` claim is in the past, `_validate_id_token` shall raise an exception, and `handle_google_callback` shall redirect to the login page without creating a Frappe session or a User record.

**Validates: Requirements 3.4, 3.5**

---

### Property 8: Claim extraction round-trip

*For any* valid Google ID token containing `email`, `given_name`, `family_name`, and `picture` claims, the values extracted by `_validate_id_token` shall equal the corresponding values in the original token payload, and the Frappe User record produced by `_provision_user` shall have an `email` field equal to the `email` claim.

**Validates: Requirements 3.6, 5.6**

---

### Property 9: Domain check is case-insensitive

*For any* email address and any allowed domains list, `_is_domain_allowed` shall return the same result regardless of the case of the domain portion of the email or the case of the entries in the allowed domains list.

**Validates: Requirements 4.5**

---

### Property 10: Disallowed domain rejects login without creating user

*For any* authenticated email whose domain is not present in a non-empty allowed domains list, `handle_google_callback` shall redirect to the login page with an error message and shall not insert a new Frappe User record.

**Validates: Requirements 4.1, 4.2**

---

### Property 11: New user provisioning sets correct fields

*For any* set of valid ID token claims (email, given_name, family_name, picture) where no Frappe User with that email exists, `_provision_user` shall create exactly one new Frappe User whose `email` matches the claim, `send_welcome_email` is `0`, and whose roles include `"Customer"`.

**Validates: Requirements 5.1, 5.3, 5.4**

---

### Property 12: Existing user is reused without modification

*For any* email address for which a Frappe User already exists, calling `_provision_user` shall return that email without inserting a new User document and without modifying the existing User document.

**Validates: Requirements 5.2**

---

### Property 13: User provisioning failure logs error and does not create session

*For any* call to `handle_google_callback` where `_provision_user` raises a Frappe exception, the handler shall call `frappe.log_error` exactly once and shall redirect to the login page without establishing a Frappe session.

**Validates: Requirements 5.5**

---

### Property 14: Login page context reflects SSO toggle state

*For any* HD Settings state, `get_login_page_context()` shall return `show_google_sso: True` if and only if `enable_google_sso` is `True`.

**Validates: Requirements 6.1, 6.3**

---

### Property 15: Settings UI disables credential fields when toggle is off

*For any* rendered `GoogleSSOSettings` component where `enable_google_sso` is `false`, the Client ID input, Client Secret input, and Allowed Domains list shall each have the `disabled` attribute set to `true`.

**Validates: Requirements 7.3**

---

### Property 16: Settings UI is read-only for non-manager users

*For any* authenticated user who does not have the Agent Manager or System Manager role, all input fields in the `GoogleSSOSettings` component shall be rendered as read-only.

**Validates: Requirements 7.5**

---

### Property 17: Network errors are logged and do not expose secrets

*For any* call to `_exchange_code_for_tokens` where the HTTP request raises an exception or returns a non-2xx response, the handler shall call `frappe.log_error` and the error message passed to `log_error` shall not contain the value of `google_client_secret`.

**Validates: Requirements 8.3, 8.5**

---

### Property 18: State is invalidated after consumption

*For any* successful call to `handle_google_callback` that passes state verification, the key `google_sso_state` shall no longer be present in `frappe.session.data` after the callback completes.

**Validates: Requirements 8.4**

---

### Property 19: Domain rejection logs domain without full email

*For any* login attempt rejected due to domain restriction, `frappe.log_error` shall be called with a message that contains the rejected domain string but does not contain the full email address (i.e., does not contain the `@` character followed by the domain).

**Validates: Requirements 8.6**

---

