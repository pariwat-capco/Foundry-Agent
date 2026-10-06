# Guard Requirement Traceability

Source document: **Technology Vendor Platform PoC Scope Proposal**, Draft V1.0, 14 Aug 2026.

Only guards with agreed priority score >= 9 are included.

| ID | Guard | Score | Source status | PoC requirement basis |
|---|---|---:|---|---|
| G01 | Role & Data Access | 10 | PDF-derived | Two-sided advisory uses role-specific perspectives; Administration includes user, role, permission and hierarchy administration. |
| G02 | Cross-Customer Data | 10 | PDF-derived/implementation interpretation | Customer 360 / Single Customer View and the same customer case are used across customer/advisor portals. |
| G03 | Human-in-the-Loop Sensitive Decision | 10 | Explicit PDF | Recommendation quality requires human final selection; AI governance says sensitive decisions stay human-in-the-loop. |
| G04 | Advisor Control & Approval | 9.5 | Explicit PDF | Advisor review, validation and approval before customer acceptance; advisors remain in control of recommendations/advice. |
| G05 | Sensitive Data Purpose | 9.5 | PDF-derived | Financial discovery, onboarding/FNA, goals, portfolio analysis and personalized recommendations require legitimate processing of customer/financial data. |
| G06 | Credentials & Secrets | 9 | Additional security control | Not explicitly stated in the PDF; added to prevent unsafe collection/storage/disclosure of authentication secrets. |
| G07 | Form Data Allowlist | 9 | PDF-derived/implementation control | Digital onboarding/FNA plus configurable workflows/business rules require controlled form/workflow data handling. |
| G08 | Form Write Validation | 9 | Implementation control supporting PDF requirements | Supports onboarding/FNA, configurable workflows, governance and reliable API/UI updates; exact write-validation algorithm is not specified by the PDF. |

## PDF trace notes

### G01 Role & Data Access
- Two-sided Advisory Journey: customer and advisor view the same underlying information from role-specific perspectives (page 4).
- Administration & Product Configuration: user, role, permission and hierarchy administration (page 5).

### G02 Cross-Customer Data
- Two-sided Advisory evidence includes Customer 360 / Single Customer View and simultaneous portals using the same customer case (page 4).
- The PDF does not explicitly say "cross-customer guard"; this is the access-control implementation needed to preserve customer-case boundaries.

### G03 Human-in-the-Loop
- PoC Success Criteria: recommendations are explainable/auditable and allow human final selection before proposal generation (page 6).
- AI governance: AI-assisted features can be controlled, reviewed and explained; sensitive decisions stay human-in-the-loop (page 6).

### G04 Advisor Control & Approval
- Two-sided Advisory Journey: advisors remain in control of recommendations and advice (page 4).
- Evidence requires advisor review, validation and approval before customer acceptance (page 4).

### G05 Sensitive Data Purpose
- Customer Experience Journey covers financial health/discovery, goals, onboarding/FNA, portfolio values, investments/contributions and personalized recommendations (page 3).
- Therefore legitimate sensitive customer/financial data must be allowed for authorized journey purposes rather than globally blocked.

### G06 Credentials & Secrets
- Additional security requirement, not directly stated by the PoC PDF.

### G07 Form Data Allowlist
- Customer Experience evidence includes digital onboarding and FNA (page 3).
- Administration includes workflow and business-rule configuration (page 5).

### G08 Form Write Validation
- The exact validation algorithm is an implementation safeguard, not a direct PDF statement.
- It supports reliable onboarding/FNA and configurable workflow execution, while avoiding incorrect automatic writes.
