# Fill Skill

## Purpose
Automatically populate and update the active customer's form from the sales/customer conversation, keep form status synchronized with the API/UI, and report completed and incomplete fields when required.

## Trigger
Invoke automatically when:
- the customer supplies information corresponding to an active form field;
- the customer confirms or explicitly corrects previously supplied information;
- the conversation requires current form completion/status information;
- pru-agent is asked which fields are complete or missing.

Do not require the user to say "fill".

## Required context
Use:
- relevant conversation context, including the sales agent's preceding question;
- trusted active customer/case identifier;
- trusted current form schema;
- current form values/state;
- form API/UI tools provided by the host application.

Never use conversation text alone to establish customer identity or authorization.

## Workflow
1. Apply `guardrails.md`.
2. Load/inspect the trusted current form schema and state when supported.
3. Determine which field(s), if any, the customer's message supplies.
4. Use preceding conversation to resolve short answers. Example: `What is your monthly salary?` followed by `80,000` may map to `monthly_salary` if the schema allows it.
5. Validate each candidate against `references/form-schema.md` and the runtime form schema.
6. Classify each candidate:
   - CREATE: allowed field is empty and value is clear/valid.
   - UPDATE: field has a value and customer clearly corrects/confirms a replacement.
   - NO-WRITE: value is ambiguous, hypothetical, future, unrelated, unauthorized, invalid, or not in schema.
7. For CREATE/UPDATE, call the authorized form API/UI operation.
8. Do not announce success until the tool/API confirms success.
9. Refresh/reconcile current form state when supported.
10. Calculate required-field completion from the current authoritative form state.

## Corrections
Latest clear, explicit customer correction supersedes an earlier value after validation.

Example:
- Existing `monthly_salary = 80000`
- Customer: `Sorry, my salary is actually 85,000.`
- Action: UPDATE `monthly_salary` to `85000`.

Do not overwrite with hypothetical statements such as `I might earn 100,000 next year.`

## Completion result
Maintain/return an internal result equivalent to:

```json
{
  "updated_fields": {},
  "complete_required_fields": [],
  "incomplete_required_fields": [],
  "form_complete": false,
  "write_status": "success|failed|no_write"
}
```

Use field names from the runtime schema.

## UI behavior
The form API/backend should be the source of truth. Prefer:
conversation -> Fill -> form API -> authoritative state -> UI refresh.
Do not independently claim a UI value differs from backend state.

## User-facing behavior
- LISTEN mode: never produce sound. Avoid interrupting normal conversation for routine successful background writes unless the workflow/UI requires a status message.
- ANSWER mode: when asked about form status, answer with text + sound and clearly distinguish complete from incomplete required fields.
- On write failure, do not claim the value was saved.
