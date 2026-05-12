# Tasks

## Task List

- [x] 1. Extend HD Settings DocType with Slack fields
  - [x] 1.1 Add four new fields to `hd_settings.json`: `integrations_tab` (Tab Break), `slack_section` (Section Break), `enable_slack_integration` (Check), `column_break_slack` (Column Break), `slack_bot_token` (Password), `slack_signing_secret` (Password), `slack_notification_channel` (Data)
  - [x] 1.2 Add validation in `hd_settings.py` `validate()`: when `enable_slack_integration` is truthy, raise `frappe.throw` if `slack_bot_token` or `slack_signing_secret` is empty

- [x] 2. Implement backend Slack API module (`helpdesk/api/slack.py`)
  - [x] 2.1 Implement `_get_slack_settings()` — reads HD Settings fields, raises `frappe.PermissionError` if signing secret is missing
  - [x] 2.2 Implement `verify_slack_request(timestamp, signature, raw_body)` — HMAC-SHA256 with `hmac.compare_digest`, rejects timestamps older than 300 s
  - [x] 2.3 Implement `_build_ticket_blocks(ticket)` — returns Slack Block Kit list with section fields (name, subject, raised_by, priority, type, URL) and actions button
  - [x] 2.4 Implement `send_ticket_notification(ticket_name)` — reads settings, checks toggle, calls `chat.postMessage` with 5 s timeout, wraps in try/except with `frappe.log_error`
  - [x] 2.5 Implement `enqueue_ticket_notification(doc, method)` — hook-compatible wrapper that calls `frappe.enqueue` for `send_ticket_notification` when integration is enabled
  - [x] 2.6 Implement `resolve_slack_user(slack_user_id)` — calls `users.info` with 5 s timeout, finds or creates Frappe User, returns email or `None` on failure
  - [x] 2.7 Implement `handle_ticket_command()` — `@frappe.whitelist(allow_guest=True)`, verifies signature, resolves user, creates HD Ticket synchronously, enqueues channel notification, returns ephemeral response

- [x] 3. Register hooks in `helpdesk/hooks.py`
  - [x] 3.1 Add `"HD Ticket": {"after_insert": "helpdesk.api.slack.enqueue_ticket_notification"}` to `doc_events`

- [x] 4. Build frontend SlackSettings component
  - [x] 4.1 Create `desk/src/components/Settings/Slack/SlackSettings.vue` — uses `createDocumentResource` on HD Settings, renders toggle + three credential inputs, disables credential fields when toggle is off, shows Unsaved badge and Save button when dirty, read-only for non-manager roles
  - [x] 4.2 Register the new component in `desk/src/components/Settings/settingsModal.ts` under the Integrations tab group with a Slack icon and `condition: () => auth.isAdmin || auth.isManager`

- [x] 5. Write backend tests (`helpdesk/tests/test_slack.py`)
  - [x] 5.1 Unit test: HD Settings JSON contains the four new Slack fields with correct fieldtype values (Req 1.1, 1.5)
  - [x] 5.2 PBT — Property 2: For random settings with toggle on and empty token or secret, assert ValidationError is raised
  - [x] 5.3 PBT — Property 1: For random tickets inserted with toggle off, assert no HTTP call is made
  - [x] 5.4 PBT — Property 3: For random ticket dicts, assert `_build_ticket_blocks` output contains all required fields and correct block structure
  - [x] 5.5 PBT — Property 4: For random tickets, mock HTTP to raise, assert `frappe.log_error` called and no exception propagates
  - [x] 5.6 PBT — Property 5: For random bodies/secrets/timestamps, assert `verify_slack_request` returns True for valid inputs and False for tampered/stale inputs
  - [x] 5.7 PBT — Property 6: For random command texts/users/channels, assert created ticket has correct subject, raised_by, priority, and description
  - [x] 5.8 PBT — Property 7: For empty/whitespace command texts and failed `users.info` responses, assert zero tickets created and ephemeral response returned
  - [x] 5.9 PBT — Property 8: For random inputs where ticket insert raises, assert `frappe.log_error` called and response text contains no Python traceback
  - [x] 5.10 PBT — Property 9: For random emails, assert `resolve_slack_user` creates a new User only when none exists, and reuses existing user otherwise
  - [x] 5.11 PBT — Property 10: For any input to `handle_ticket_command`, assert returned dict has `response_type == "ephemeral"`
  - [x] 5.12 Unit test: assert `frappe.enqueue` is called (not direct HTTP) in the `after_insert` path (Req 2.3)
  - [x] 5.13 Unit test: assert `timeout=5` is passed in all `requests.get/post` calls in `slack.py` (Req 5.4)
  - [x] 5.14 Unit test: assert `hmac.compare_digest` is used in `verify_slack_request` (Req 3.4)

- [ ] 6. Write frontend tests (`desk/src/components/Settings/Slack/__tests__/SlackSettings.spec.ts`)
  - [ ] 6.1 Unit test: component mounts and renders the "Slack Integration" section heading (Req 7.1, 7.2)
  - [ ] 6.2 PBT — Property 11: For toggle=false state, assert Bot Token, Signing Secret, and Channel inputs all have disabled=true
  - [ ] 6.3 PBT — Property 12: For non-manager user auth state, assert all inputs are read-only
  - [ ] 6.4 Unit test: after successful save, a toast confirmation message is displayed (Req 7.4)
