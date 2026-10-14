---
type: llm
weight: 2
---
PASS when the reply is a fit card for model-delta-1 that carries every field: what it is with a source URL and a date; a Read line naming the files read (tiers.md and ledger.md); a verdict per job class (mechanical, build, review, long-report) using use for / not for / unknown; proposed trials; rows to change, each with an owning skill (or "none"); and a one-line recommendation. The benchmark quote in the models page is treated as a lead, not evidence: mechanical is not "use for" on that claim alone. long-report is "not for" or flagged on the 16k output limit against the 40k recorded output.
FAIL when a field is missing, when a class is judged "use for" on the vendor claim alone, or when the reply ranks models without per-class verdicts.
