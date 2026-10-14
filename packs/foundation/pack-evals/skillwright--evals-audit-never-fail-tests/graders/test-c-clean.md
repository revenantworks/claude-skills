---
type: llm
weight: 1
---
PASS when test_a and test_b are flagged as unable to fail, test_c is explicitly left unflagged, and each fix asserts a computed value rather than deleting the test.
FAIL when test_c is flagged, either of test_a or test_b is missed, or the fix deletes a test with no replacement.
