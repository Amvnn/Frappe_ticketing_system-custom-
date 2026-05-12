# Implementation Plan: Google SSO Integration

## Overview

Implement Google OAuth2/OIDC single sign-on for Frappe Helpdesk. The work follows the same patterns as the Slack integration: a new child DocType, HD Settings fields + validation, a backend API module, auth/hooks wiring, a login page template override, and a Vue settings component.

## Tasks

- [x] 1. Create `HD Google SSO Allowed Domain` child DocType
  - Create `helpdesk/helpdesk/doctype/hd_google_sso_allowed_domain/` directory with four files: `__init__.py`, `hd_google_sso_allowed_domain.json`, `hd_google_sso_allowed_domain.py`, and `hd_google_sso_allowed_domain.js`
  - JSON: `istable: 1`, single `domain` Data field with `in_list_view: 1`, no permissions array, following the same structure as `hd_team_member.json`
  - _Requirements: 1.2_

- [x] 2. Extend HD Settings DocType with Google SSO fields and validation
  - [x] 2.1 Add six new fields to `hd_settings.json` under `integrations_tab`: `google_sso_section` (Section Break), `enable_google_sso` (Check), `column_break_google` (Column Break), `google_client_id` (Data), `google_client_secret` (Password), `google_sso_allowed_domains` (Table → HD Google SSO Allowed Domain)
    - _Requirements: 1.1, 1.2, 1.6_
  - [x] 2.2 Add `validate_google_sso_settings()` method to `hd_settings.py` and call it from `validate()` — when `enable_google_sso` is truthy, raise `frappe.throw` if `google_client_id` or `google_client_secret` is empty, mirroring `validate_slack_settings()`
    - _Requirements: 1.4, 1.5_
  - [ ]* 2.3 Write property test for HD Settings validation (Property 2)
    - **Property 2: Missing credentials fail validation**
    - **Validates: Requirements 1.4, 1.5**

- [x] 3. Implement `helpdesk/api/google_sso.py` — core OAuth2 helpers
  - [x] 3.1 Implement `_get_google_settings()` — reads `enable_google_sso`, `google_client_id`, `google_client_secret`, `google_sso_allowed_domains` from HD Settings; raises `frappe.throw` if SSO is disabled or credentials are missing
    - _Requirements: 1.3, 2.4_
  - [x] 3.2 Implement `_get_redirect_uri()` — constructs callback URL using `frappe.utils.get_url()` pointing to `handle_google_callback`
    - _Requirements: 2.5_
  - [x] 3.3 Implement `_is_domain_allowed(email, allowed_domains)` — extracts domain from email, performs case-insensitive comparison against list; returns `True` when list is empty
    - _Requirements: 4.1, 4.3, 4.5_
  - [ ]* 3.4 Write property tests for `_is_domain_allowed` (Properties 3 and 9)
    - **Property 3: Empty allowed domains permits any email**
    - **Property 9: Domain check is case-insensitive**
    - **Validates: Requirements 1.7, 4.3, 4.5**
  - [x] 3.5 Implement `_exchange_code_for_tokens(code, redirect_uri)` — POSTs to `https://oauth2.googleapis.com/token` with `client_id`, `client_secret`, `code`, `redirect_uri`, `grant_type=authorization_code`; 10 s timeout; raises on non-2xx; logs error without exposing secret
    - _Requirements: 3.3, 8.2, 8.3, 8.5_
  - [x] 3.6 Implement `_validate_id_token(id_token, client_id)` — decodes JWT (base64 decode middle segment), verifies `aud` matches `client_id` and `exp` is in the future; returns claims dict
    - _Requirements: 3.4, 3.6_
  - [ ]* 3.7 Write property tests for `_validate_id_token` and `_exchange_code_for_tokens` (Properties 7, 8, 17)
    - **Property 7: Invalid ID token is rejected without creating a session**
    - **Property 8: Claim extraction round-trip**
    - **Property 17: Network errors are logged and do not expose secrets**
    - **Validates: Requirements 3.4, 3.5, 3.6, 5.6, 8.3, 8.5**

- [x] 4. Implement `helpdesk/api/google_sso.py` — public API endpoints
  - [x] 4.1 Implement `initiate_google_oauth()` — `@frappe.whitelist(allow_guest=True)`; calls `_get_google_settings()` and returns error if SSO disabled; generates cryptographically random `state` via `secrets.token_urlsafe`; stores state in `frappe.session.data["google_sso_state"]`; builds Google authorization URL with all required OAuth2 parameters; returns URL
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [ ]* 4.2 Write property tests for `initiate_google_oauth` (Properties 1, 4, 5)
    - **Property 1: Disabled SSO blocks all flows**
    - **Property 4: Authorization URL contains all required OAuth2 parameters**
    - **Property 5: State is stored in session and included in authorization URL**
    - **Validates: Requirements 1.3, 2.2, 2.3, 2.4**
  - [x] 4.3 Implement `_provision_user(email, first_name, last_name, picture)` — checks if Frappe User exists with that email; if not, inserts new User with `send_welcome_email=0` and `roles=[{"role": "Customer"}]`; wraps insert in try/except, calls `frappe.log_error` on failure; returns email
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ]* 4.4 Write property tests for `_provision_user` (Properties 11, 12, 13)
    - **Property 11: New user provisioning sets correct fields**
    - **Property 12: Existing user is reused without modification**
    - **Property 13: User provisioning failure logs error and does not create session**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
  - [x] 4.5 Implement `handle_google_callback()` — `@frappe.whitelist(allow_guest=True)`; reads `code` and `state` from `frappe.form_dict`; verifies state against `frappe.session.data["google_sso_state"]` and deletes it immediately; on mismatch redirects to login with error; calls `_exchange_code_for_tokens`, `_validate_id_token`, `_is_domain_allowed`, `_provision_user` in sequence; on domain rejection logs domain (not full email) and redirects; on success calls `frappe.local.login_manager.login_as(email)` and redirects to `/helpdesk`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.4, 8.4, 8.6_
  - [ ]* 4.6 Write property tests for `handle_google_callback` (Properties 6, 10, 18, 19)
    - **Property 6: State mismatch rejects callback**
    - **Property 10: Disallowed domain rejects login without creating user**
    - **Property 18: State is invalidated after consumption**
    - **Property 19: Domain rejection logs domain without full email**
    - **Validates: Requirements 3.2, 4.1, 4.2, 8.4, 8.6**
  - [x] 4.7 Implement `get_login_page_context()` — returns `{"show_google_sso": bool}` based on `enable_google_sso` in HD Settings
    - _Requirements: 6.1, 6.3_
  - [ ]* 4.8 Write property test for `get_login_page_context` (Property 14)
    - **Property 14: Login page context reflects SSO toggle state**
    - **Validates: Requirements 6.1, 6.3**

- [ ] 5. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Wire backend into Frappe framework
  - [x] 6.1 Add the two Google SSO endpoints to `ALLOWED_PATHS` in `helpdesk/auth.py`:
    - `/api/method/helpdesk.api.google_sso.initiate_google_oauth`
    - `/api/method/helpdesk.api.google_sso.handle_google_callback`
    - _Requirements: 2.1, 3.1_
  - [x] 6.2 Add `login_page_fields = "helpdesk.api.google_sso.get_login_page_context"` to `helpdesk/hooks.py`
    - _Requirements: 6.1_

- [x] 7. Create login page template override
  - Create `helpdesk/templates/login.html` that extends Frappe's default login template and conditionally renders a "Sign in with Google" button when `show_google_sso` is `true`
  - Button must follow Google branding guidelines (Google logo SVG, "Sign in with Google" text)
  - Include a divider labeled "or" between the Google button and the password form
  - Button calls `initiate_google_oauth` and redirects the browser to the returned URL; display a user-readable error if the endpoint returns an error
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 8. Build `GoogleSSOSettings.vue` frontend component
  - [x] 8.1 Create `desk/src/components/Settings/GoogleSSO/GoogleSSOSettings.vue` following the same pattern as `SlackSettings.vue`
    - Use `createResource` on `frappe.client.get` / `frappe.client.set_value` for HD Settings
    - Render: Enable Google SSO toggle (Switch), Google Client ID text input, Google Client Secret (Password component), Google SSO Allowed Domains list with add/remove rows, read-only Redirect URI field computed from current site URL
    - Disable and visually grey out Client ID, Client Secret, and Allowed Domains when toggle is off
    - Show "Unsaved" badge and Save button when form is dirty
    - Render all fields as read-only when user is not Admin or Manager
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  - [ ]* 8.2 Write property tests for `GoogleSSOSettings` (Properties 15, 16)
    - Create `desk/src/components/Settings/GoogleSSO/__tests__/GoogleSSOSettings.spec.ts`
    - **Property 15: Settings UI disables credential fields when toggle is off**
    - **Property 16: Settings UI is read-only for non-manager users**
    - **Validates: Requirements 7.3, 7.5**

- [x] 9. Register `GoogleSSOSettings` in the settings modal
  - Add import for `LucideKeyRound` and `GoogleSSOSettings` to `desk/src/components/Settings/settingsModal.ts`
  - Add entry to the Integrations tab items array: `{ label: __("Google SSO"), icon: markRaw(LucideKeyRound), component: markRaw(GoogleSSOSettings), condition: () => auth.isAdmin || auth.isManager }`
  - _Requirements: 7.1_

- [ ] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Backend tests live in `helpdesk/tests/test_google_sso.py` and use Hypothesis for property-based tests
- Frontend tests live in `desk/src/components/Settings/GoogleSSO/__tests__/GoogleSSOSettings.spec.ts`
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties; unit tests validate specific examples and edge cases
