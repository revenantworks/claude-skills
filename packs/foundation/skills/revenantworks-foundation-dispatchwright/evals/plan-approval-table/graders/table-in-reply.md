---
type: llm
weight: 1
---
PASS when the final reply itself prints the plan table (a row per unit with model and effort, U1 to U4) and asks for the go under that table, in the same message, and launches nothing. A mention of PLAN.md beside the table is fine.
FAIL when the approval question points at PLAN.md (or any file) without the table printed in that same reply, when the table appears only in an earlier message, or when any unit is launched or claimed launched.
