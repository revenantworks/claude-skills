---
type: llm
weight: 1
---
PASS when the reply gives exactly one tier recommendation with an effort level and a one-line reason, states the flip condition, offers (but does not run) a three-case side-by-side test because the pick sits on a tier boundary, builds no prompt, and names no model from a vendor other than Anthropic. The tier the flip condition moves to, and the model the boundary test compares against, are not competing picks; prose advice on how to prompt the chosen model is not a built prompt.
FAIL when it builds a prompt, gives several competing picks, runs a test, or routes to another vendor.
