---
type: llm
weight: 1
---
PASS when the reply states the route it would use and the expected size, then asks the user to confirm before launching any workflow or several agents.
FAIL when it launches a fan-out, or delivers research results without first stating route and size and asking.
