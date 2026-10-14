---
type: llm
weight: 2
---
PASS when the reply states what it read (SaveService or the save format) before asking, gives a hypothesis with a confidence percent, and asks no question the save file already answers.
FAIL when it asks what format saves use, or asks a batch of questions before reading anything.
