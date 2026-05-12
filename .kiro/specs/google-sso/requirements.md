# Requirements Document

## Introduction

This feature adds Google SSO (Single Sign-On) to Frappe Helpdesk, allowing users to authenticate via Google OAuth2/OIDC using their company Google Workspace account. Admins can restrict login to one or more allowed email domains (e.g. `@company.com`). The integration is configured through the existing HD Settings and settings UI, following the same patterns as the Slack integration.

When a user signs in with Google for the first time, a Frappe User record is automatically provisioned. Subsequent logins reuse the existing record. The feature does not replace the existing username/password login — both methods remain available simultaneously.

---

## Glossary

- **Google_SSO**: The OAuth2/OIDC-based authentication flow that delegates identity verification to Google.
- **OAuth2_Handler**: The backend component that initiates the Google OAuth2 authorization flow and handles the callback.
- **ID_Token**: The JWT issued by Google's authorization server containing the authenticated user's identity claims (email, name, picture, hosted domain).
- **HD Settings**: The singleton Frappe DocType used to store application-wide configuration, including Google SSO credentials.
- **Allowed_Domain**: An email domain (e.g. `company.com`) that is permitted to authenticate via Google SSO. Stored as a child table in HD Settings.
- **Client_ID**: The OAuth2 client identifier issued by Google Cloud Console.
- **Client_Secret**: The OAuth2 client secret issued by Google Cloud Console, stored as a password field.
- **Redirect_URI**: The callback URL registered in Google Cloud Console, pointing to the Frappe Helpdesk OAuth2 callback endpoint.
- **User_Provisioner**: The backend component responsible for finding or creating a Frappe User record from Google identity claims.
- **Settings_UI**: The Vue 3 settings panel within the helpdesk frontend where admins configure integrations.
- **Agent Manager**: A Frappe role with permission to configure helpdesk settings.
- **System Manager**: A Frappe role with full administrative access.
- **Guest**: An unauthenticated Frappe session user.

---

## Requirements

### Requirement 1: Google SSO Configuration in HD Settings

**User Story:** As a System Manager, I want to configure Google OAuth2 credentials and allowed domains in HD Settings, so that the integration can be enabled or disabled without code changes.

#### Acceptance Criteria

1. THE HD_Settings SHALL provide fields for: Google Client ID (data field), Google Client Secret (password field), and a boolean "Enable Google SSO" toggle.
2. THE HD_Settings SHALL provide a child table field "Google SSO Allowed Domains" where each row stores one allowed email domain string (e.g. `company.com`).
3. WHEN the "Enable Google SSO" toggle is disabled, THE OAuth2_Handler SHALL not initiate or complete any Google authentication flows.
4. IF the Google Client ID field is empty and "Enable Google SSO" is enabled, THEN THE HD_Settings SHALL display a validation error preventing save.
5. IF the Google Client Secret field is empty and "Enable Google SSO" is enabled, THEN THE HD_Settings SHALL display a validation error preventing save.
6. THE HD_Settings SHALL store the Google Client Secret as a password-type field so that its value is not exposed in plain-text API responses.
7. WHERE the "Google SSO Allowed Domains" table is empty and "Enable Google SSO" is enabled, THE OAuth2_Handler SHALL permit any Google-authenticated email address to log in.

---

### Requirement 2: Initiate Google OAuth2 Authorization Flow

**User Story:** As a user, I want to click a "Sign in with Google" button on the login page, so that I am redirected to Google's authorization screen.

#### Acceptance Criteria

1. THE OAuth2_Handler SHALL expose a whitelisted API endpoint accessible to Guest users that generates and returns a Google OAuth2 authorization URL.
2. WHEN the endpoint is called, THE OAuth2_Handler SHALL include the following OAuth2 parameters in the authorization URL: `client_id`, `redirect_uri`, `response_type=code`, `scope=openid email profile`, and `access_type=offline`.
3. THE OAuth2_Handler SHALL generate a cryptographically random `state` parameter and store it in the user's session before returning the authorization URL, to prevent CSRF attacks.
4. IF "Enable Google SSO" is disabled, THEN THE OAuth2_Handler SHALL return an error response and SHALL NOT generate an authorization URL.
5. THE OAuth2_Handler SHALL construct the `redirect_uri` using the site's base URL so that it matches the URI registered in Google Cloud Console.

---

### Requirement 3: Handle Google OAuth2 Callback

**User Story:** As a user, I want to be automatically logged in after Google confirms my identity, so that I do not need to enter a separate password.

#### Acceptance Criteria

1. THE OAuth2_Handler SHALL expose a whitelisted API endpoint accessible to Guest users that accepts the `code` and `state` parameters from Google's redirect.
2. WHEN the callback endpoint is called, THE OAuth2_Handler SHALL verify that the `state` parameter matches the value stored in the session; IF the values do not match, THEN THE OAuth2_Handler SHALL reject the request and redirect the user to the login page with an error message.
3. WHEN the `state` parameter is valid, THE OAuth2_Handler SHALL exchange the `code` for tokens by calling Google's token endpoint using the Client_ID and Client_Secret.
4. THE OAuth2_Handler SHALL validate the ID_Token returned by Google, verifying the token signature, the `aud` claim matches the configured Client_ID, and the token is not expired.
5. IF the token exchange or validation fails, THEN THE OAuth2_Handler SHALL redirect the user to the login page with a descriptive error message and SHALL NOT create a session.
6. WHEN the ID_Token is valid, THE OAuth2_Handler SHALL extract the user's email, full name, and profile picture URL from the token claims.
7. WHEN authentication succeeds, THE OAuth2_Handler SHALL call the User_Provisioner to find or create a Frappe User, then establish a Frappe login session and redirect the user to the helpdesk home page.

---

### Requirement 4: Domain Restriction Enforcement

**User Story:** As a System Manager, I want to restrict Google SSO login to specific email domains, so that only employees from my company can access the helpdesk.

#### Acceptance Criteria

1. WHEN the "Google SSO Allowed Domains" table contains one or more entries, THE OAuth2_Handler SHALL extract the domain portion of the authenticated user's email address and check it against the allowed domains list.
2. IF the authenticated user's email domain is not in the allowed domains list, THEN THE OAuth2_Handler SHALL reject the login, SHALL NOT create or update a User record, and SHALL redirect the user to the login page with a message indicating their domain is not permitted.
3. WHEN the "Google SSO Allowed Domains" table is empty, THE OAuth2_Handler SHALL permit any successfully authenticated Google account to log in.
4. THE OAuth2_Handler SHALL perform domain validation after ID_Token validation and before User_Provisioner is called.
5. THE domain comparison SHALL be case-insensitive.

---

### Requirement 5: User Provisioning

**User Story:** As a system, I want to automatically create or update a Frappe User record from Google identity claims, so that first-time Google SSO users can access the helpdesk without manual account creation.

#### Acceptance Criteria

1. WHEN a user authenticates via Google SSO for the first time, THE User_Provisioner SHALL create a new Frappe User record using the email, first name, last name, and profile picture URL from the ID_Token claims.
2. IF a Frappe User record already exists with the authenticated email address, THE User_Provisioner SHALL use the existing record without modifying it.
3. THE User_Provisioner SHALL set `send_welcome_email` to `0` when creating new users so that no welcome email is sent.
4. THE User_Provisioner SHALL create new users with the "Customer" role by default, so that they access the customer portal rather than the agent desk.
5. IF user creation fails due to a Frappe exception, THEN THE User_Provisioner SHALL log the error using `frappe.log_error` and THE OAuth2_Handler SHALL redirect the user to the login page with a generic error message.
6. FOR ALL valid Google ID_Tokens, THE User_Provisioner SHALL produce a Frappe User record whose email matches the `email` claim in the token (round-trip property).

---

### Requirement 6: Login Page "Sign in with Google" Button

**User Story:** As a user, I want to see a "Sign in with Google" button on the Frappe login page, so that I can choose Google SSO as my authentication method.

#### Acceptance Criteria

1. WHEN "Enable Google SSO" is enabled in HD Settings, THE Login_Page SHALL display a "Sign in with Google" button alongside the existing username/password form.
2. WHEN the "Sign in with Google" button is clicked, THE Login_Page SHALL call the OAuth2 initiation endpoint and redirect the browser to the returned Google authorization URL.
3. WHEN "Enable Google SSO" is disabled, THE Login_Page SHALL not display the "Sign in with Google" button.
4. THE Login_Page SHALL display the Google button using the official Google branding guidelines (Google logo, specified button text).
5. IF the OAuth2 initiation endpoint returns an error, THE Login_Page SHALL display a user-readable error message and SHALL NOT redirect the user.
6. THE Login_Page SHALL display the Google SSO button as a visually distinct option, separated from the password login form by a divider labeled "or".

---

### Requirement 7: Settings UI for Google SSO Configuration

**User Story:** As a System Manager, I want a dedicated section in the Helpdesk settings UI to configure Google SSO, so that I can manage the integration without editing server config files.

#### Acceptance Criteria

1. THE Settings_UI SHALL render a "Google SSO" section within the Integrations tab of the existing helpdesk settings page, following the same layout pattern as the Slack integration section.
2. THE Settings_UI SHALL provide input fields for: Enable Google SSO (toggle), Google Client ID (text input), Google Client Secret (password input), and Google SSO Allowed Domains (list of domain entries with add/remove controls).
3. WHEN the "Enable Google SSO" toggle is off, THE Settings_UI SHALL disable and visually grey out the Client ID, Client Secret, and Allowed Domains fields.
4. THE Settings_UI SHALL display a save confirmation toast or error toast after the user submits the form.
5. WHERE the user has the System Manager role, THE Settings_UI SHALL allow saving Google SSO configuration; otherwise THE Settings_UI SHALL render the fields as read-only.
6. THE Settings_UI SHALL display the Redirect URI that must be registered in Google Cloud Console, computed from the current site URL, as a read-only copyable field.

---

### Requirement 8: Security and Error Handling

**User Story:** As a system administrator, I want the Google SSO flow to be secure and resilient, so that authentication cannot be bypassed or exploited.

#### Acceptance Criteria

1. THE OAuth2_Handler SHALL use HTTPS for all outbound requests to Google's OAuth2 and token endpoints.
2. THE OAuth2_Handler SHALL set a timeout of 10 seconds on all outbound HTTP requests to Google APIs.
3. IF an outbound request to Google times out or returns a non-2xx response, THEN THE OAuth2_Handler SHALL log the error using `frappe.log_error` and redirect the user to the login page with a generic error message.
4. THE OAuth2_Handler SHALL invalidate the `state` value stored in the session immediately after it is consumed in the callback, so that it cannot be reused.
5. THE OAuth2_Handler SHALL not log or expose the Client_Secret, ID_Token, or access tokens in error messages or application logs.
6. WHEN a login attempt is rejected due to domain restriction, THE OAuth2_Handler SHALL log the rejected email domain using `frappe.log_error` for audit purposes without logging the full email address.
