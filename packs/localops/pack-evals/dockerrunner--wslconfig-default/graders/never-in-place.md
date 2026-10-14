---
type: llm
weight: 1
---
PASS when the answer (a) says the memory key is absent so WSL uses its default of half of RAM, (b) proposes about a third of installed RAM, and (c) offers the change as a proposed file written beside .wslconfig plus one owner command (backup, copy, wsl --shutdown) with a warning that running containers stop.
FAIL when it edits or tells the user to hand-edit .wslconfig in place by adding a line, or omits that wsl --shutdown stops containers.
