# Form Schema Reference

This file defines the contract expected by Fill. Replace the example/placeholder fields below with the actual runtime form schema when available. The runtime trusted schema is authoritative.

## Required metadata per field
- `field_name`: canonical API/form field key.
- `label`: user-facing label.
- `type`: string, number, date, enum, boolean, etc.
- `required`: true/false.
- `sensitive`: classification if applicable.
- `fill_allowed`: true/false.
- `validation`: format/range/allowed-value rules.
- `normalization`: deterministic conversions permitted before write.

## Example only

| field_name | label | type | required | sensitive | fill_allowed | validation |
|---|---|---|---|---|---|---|
| first_name | First name | string | true | personal | true | non-empty |
| last_name | Last name | string | true | personal | true | non-empty |
| monthly_salary | Monthly salary | number | true | financial | true | runtime business rules |

## Rules
1. Do not treat example fields as the complete production schema.
2. Do not create fields absent from the trusted runtime schema.
3. Sensitive does not mean automatically blocked. Apply the Sensitive Data Purpose Guard.
4. Credentials/secrets are never fillable even if mentioned in conversation.
5. If normalization is not explicitly deterministic, preserve the source value or request clarification rather than guessing.
