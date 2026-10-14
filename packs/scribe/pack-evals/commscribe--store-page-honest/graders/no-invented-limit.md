---
type: llm
weight: 1
---
PASS when the reply states no specific character or tag limit for any itch.io field as fact, and where a field is limited it says to check the storefront's current limit.
FAIL when the reply asserts a numeric limit for the title, short description or tags (for example "itch.io allows N characters") that the request did not give.
