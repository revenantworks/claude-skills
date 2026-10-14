---
type: llm
weight: 2
---
PASS when the reply contains one complete HTML file that uses inline SVG, loads nothing from outside (no "src=", no "<script", no "<link", no "@import", and no http or https URL other than the SVG namespace declaration), shows each of the four rows exactly once in a table, and marks T-0590 as a rumour (dashed or labelled).
FAIL when the reply gives no complete file, loads any external library, font or stylesheet, invents an event or date not in the four rows, or states the rumour as fact.
