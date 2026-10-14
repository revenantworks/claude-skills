---
type: llm
focus: last_message
weight: 2
---

PASS if the brief carries a states section or table that specifies the empty, loading, error and long-content (many orders, or a long item name) states of the screen, each with what the user sees, AND it names colour roles (such as ground, surface, text, accent) without choosing any hex value, rgb value or font family. FAIL if any of those four states is missing, or if the brief picks a concrete colour value or a named font family.
