# Requirements Document

## Introduction

This feature adds Slack integration to Frappe Helpdesk for a DevOps ticketing system. It covers two capabilities:

1. **Webhook Notifications** — When a new HD Ticket is created, the Notification_Service automatically posts a structured message to a configured Slack channel (e.g. `#devops-tickets`) containing ticket details and a direct link.
2. **Slash Command Ticket Creation** — A Slack app exposes a `/ticket` slash command that calls a Frappe API endpoint, allowing DevOps team members to raise tickets directly from Slack without opening a browser.

Configuration (webhook URL, bot token, signing secret, target channel) is stored in HD Settings and managed by an Agent Manager or System Manager.

---

## Glossary

- **HD Ticket**: The Frappe DocType representing a helpdesk support ticket.
- **Notification_Service**: The backend component responsible for sending outbound Slack messages.
- **Slash_Command_Handler**: The Frappe API endpoint that receives and processes `/ticket` slash commands from Slack.
- **Slack_App**: The custom Slack application configured with a slash command and bot token.
- **HD Settings**: The singleton Frappe DocType used to store application-wide configuration, including Slack credentials.
- **Agent Manager**: A Frappe role with permission to configure helpdesk settings.
- **Signing_Secret**: The Slack-provided secret used to verify that incoming requests originate from Slack.
- **Bot_Token**: The Slack OAuth bot token used to authenticate outbound API calls to Slack.
- **Webhook_URL**: An optional incoming webhook URL for posting messages without a bot token.
- **Raised_By**: The email address of the user who created the ticket.

---

## Requirements

### Requirement 1: Slack Configuration in HD Settings

**User Story:** As an Agent Manager, I want to configure Slack credentials and target channel in HD Settings, so that the integration can be enabled or disabled without code changes.

#### Acceptance Criteria

1. THE HD_Settings SHALL provide fields for: Slack Bot Token, Slack Signing Secret, Slack Notification Channel, and a boolean "Enable Slack Integration" toggle.
2. WHEN the "Enable Slack Integration" toggle is disabled, THE Notification_Service SHALL not send any outbound Slack messages.
3. IF the Slack Bot Token field is empty and "Enable Slack Integration" is enabled, THEN THE HD_Settings SHALL display a validation error preventing save.
4. IF the Slack Signing Secret field is empty and "Enable Slack Integration" is enabled, THEN THE HD_Settings SHALL display a validation error preventing save.
5. THE HD_Settings SHALL store the Slack Bot Token and Slack Signing Secret as password-type fields so that their values are not exposed in API responses.

---

### Requirement 2: New Ticket Slack Notification

**User Story:** As a DevOps team member, I want a Slack notification posted to `#devops-tickets` when a new ticket is created, so that the team is immediately aware without monitoring the helpdesk UI.

#### Acceptance Criteria

1. WHEN a new HD Ticket is inserted and "Enable Slack Integration" is enabled, THE Notification_Service SHALL post a message to the configured Slack Notification Channel.
2. THE Notification_Service SHALL include the following fields in the Slack message: ticket name (ID), subject, raised_by, priority, ticket type, and a direct URL to the ticket in the helpdesk UI.
3. THE Notification_Service SHALL send the Slack notification asynchronously using a background job so that ticket creation is not blocked or slowed by the outbound HTTP call.
4. IF the outbound HTTP request to Slack fails, THEN THE Notification_Service SHALL log the error using `frappe.log_error` and SHALL NOT raise an exception that rolls back the ticket insert.
5. IF "Enable Slack Integration" is disabled, THEN THE Notification_Service SHALL skip sending the notification without logging an error.
6. THE Notification_Service SHALL format the Slack message using Slack Block Kit with a section block for ticket details and an action button linking to the ticket.

---

### Requirement 3: Slack Request Signature Verification

**User Story:** As a system administrator, I want all incoming Slack slash command requests to be cryptographically verified, so that only legitimate Slack requests are processed.

#### Acceptance Criteria

1. WHEN a request arrives at the Slash_Command_Handler, THE Slash_Command_Handler SHALL verify the `X-Slack-Signature` header using HMAC-SHA256 with the configured Signing_Secret.
2. THE Slash_Command_Handler SHALL reject requests where the `X-Slack-Request-Timestamp` header is more than 300 seconds old, returning an HTTP 403 response.
3. IF the computed HMAC signature does not match the `X-Slack-Signature` header value, THEN THE Slash_Command_Handler SHALL return an HTTP 403 response and SHALL NOT create a ticket.
4. THE Slash_Command_Handler SHALL use a constant-time comparison function when comparing HMAC signatures to prevent timing attacks.
5. IF the Signing_Secret is not configured in HD Settings, THEN THE Slash_Command_Handler SHALL return an HTTP 403 response.

---

### Requirement 4: Slash Command Ticket Creation

**User Story:** As a DevOps team member, I want to run `/ticket <description>` in Slack to create a helpdesk ticket, so that I can report issues without leaving Slack.

#### Acceptance Criteria

1. WHEN a valid `/ticket <description>` command is received and signature verification passes, THE Slash_Command_Handler SHALL create a new HD Ticket with the command text as the subject.
2. THE Slash_Command_Handler SHALL set the ticket's `raised_by` field to the email address of the Slack user who issued the command, resolved via the Slack `users.info` API.
3. THE Slash_Command_Handler SHALL set the ticket's `priority` to "Medium" by default when no priority is specified in the command text.
4. THE Slash_Command_Handler SHALL set the ticket's `description` to include the full command text, the Slack username, and the originating channel name.
5. WHEN the ticket is created successfully, THE Slash_Command_Handler SHALL return an ephemeral Slack response containing the ticket ID and a button linking to the ticket in the helpdesk UI.
6. IF the command text is empty, THEN THE Slash_Command_Handler SHALL return an ephemeral Slack response with usage instructions and SHALL NOT create a ticket.
7. IF the Slack `users.info` API call fails or returns no email, THEN THE Slash_Command_Handler SHALL return an ephemeral error response and SHALL NOT create a ticket.
8. IF ticket creation fails due to a Frappe exception, THEN THE Slash_Command_Handler SHALL log the error using `frappe.log_error` and return an ephemeral Slack response describing the failure.

---

### Requirement 5: Slack User Resolution

**User Story:** As a system, I want to resolve a Slack user's identity to a Frappe user account, so that tickets created via Slack are attributed to the correct person.

#### Acceptance Criteria

1. WHEN a slash command is received, THE Slash_Command_Handler SHALL call the Slack `users.info` API using the Bot_Token to retrieve the Slack user's email address.
2. IF a Frappe User record with the resolved email address exists, THE Slash_Command_Handler SHALL use that email as `raised_by` without creating a new user.
3. IF no Frappe User record exists for the resolved email, THE Slash_Command_Handler SHALL create a new Frappe User record with the email and Slack display name before creating the ticket.
4. THE Slash_Command_Handler SHALL set a timeout of 5 seconds on all outbound HTTP requests to the Slack API.
5. IF the Slack API returns `ok: false`, THEN THE Slash_Command_Handler SHALL treat the user resolution as failed and return an ephemeral error response.

---

### Requirement 6: Slash Command Response Format

**User Story:** As a DevOps team member, I want the `/ticket` command to respond with a clear, structured confirmation, so that I know the ticket was created and can navigate to it immediately.

#### Acceptance Criteria

1. THE Slash_Command_Handler SHALL return all responses as `application/json` with `response_type: "ephemeral"` so that only the invoking user sees the response.
2. WHEN a ticket is created successfully, THE Slash_Command_Handler SHALL include the ticket name, a truncated subject preview (maximum 100 characters), and a "Open in Helpdesk" button in the response.
3. THE Slash_Command_Handler SHALL return the response within the Slack 3-second timeout window by performing ticket creation synchronously and deferring the channel notification to a background job.
4. IF an error occurs, THE Slash_Command_Handler SHALL return a human-readable error message in the ephemeral response without exposing internal stack traces.

---

### Requirement 7: Settings UI for Slack Configuration

**User Story:** As an Agent Manager, I want a dedicated section in the Helpdesk settings UI to configure Slack, so that I can manage the integration without editing server config files.

#### Acceptance Criteria

1. THE Settings_UI SHALL render a "Slack Integration" section within the existing helpdesk settings page.
2. THE Settings_UI SHALL provide input fields for: Enable Slack Integration (toggle), Slack Bot Token (password input), Slack Signing Secret (password input), and Slack Notification Channel (text input).
3. WHEN the "Enable Slack Integration" toggle is off, THE Settings_UI SHALL disable and visually grey out the Bot Token, Signing Secret, and Channel fields.
4. THE Settings_UI SHALL display a save confirmation or error message after the user submits the form.
5. WHERE the user has the Agent Manager role, THE Settings_UI SHALL allow saving Slack configuration; otherwise THE Settings_UI SHALL render the fields as read-only.
